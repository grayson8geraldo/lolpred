"""
Data Loader - Downloads and parses Oracle's Elixir CSV data.

Oracle's Elixir (https://oracleselixir.com) provides free professional
LoL esports match data with 100+ columns per row, updated daily.

Data structure: Each game has 12 rows (2 team rows + 10 player rows).
Team rows have position='team', player rows have lane positions.
"""

import os
import pandas as pd
import gdown
from config import ORACLE_ELIXIR_URLS, ALL_TOP_LEAGUE_IDS, DATA_DIR


def download_data(years: list[int], force: bool = False) -> None:
    """Download Oracle's Elixir CSV files for specified years."""
    os.makedirs(DATA_DIR, exist_ok=True)

    for year in years:
        filepath = os.path.join(DATA_DIR, f"{year}_matches.csv")
        if os.path.exists(filepath) and not force:
            print(f"  {year}: already exists, skipping (use --force to re-download)")
            continue

        url = ORACLE_ELIXIR_URLS.get(year)
        if not url:
            print(f"  {year}: no download URL configured, skipping")
            continue

        print(f"  {year}: downloading from Oracle's Elixir...")
        try:
            gdown.download(url, filepath, quiet=True)
            print(f"  {year}: saved to {filepath}")
        except Exception as e:
            print(f"  {year}: download failed - {e}")


def load_data(years: list[int]) -> pd.DataFrame:
    """Load and concatenate CSV data for specified years."""
    frames = []
    for year in years:
        filepath = os.path.join(DATA_DIR, f"{year}_matches.csv")
        if not os.path.exists(filepath):
            print(f"  Warning: {filepath} not found, skipping")
            continue
        print(f"  Loading {year} data...")
        df = pd.read_csv(filepath, low_memory=False)
        frames.append(df)

    if not frames:
        raise FileNotFoundError(
            "No data files found. Run 'python main.py download' or "
            "'python main.py generate' first."
        )

    return pd.concat(frames, ignore_index=True)


def generate_and_save_sample_data(years: list[int] = None) -> None:
    """Generate sample data and save as CSV files for testing."""
    from src.sample_data import generate_sample_data

    if years is None:
        years = [2024, 2025]

    os.makedirs(DATA_DIR, exist_ok=True)
    df = generate_sample_data(years)

    for year in years:
        year_df = df[df["year"] == year]
        filepath = os.path.join(DATA_DIR, f"{year}_matches.csv")
        year_df.to_csv(filepath, index=False)
        print(f"  {year}: generated {len(year_df)} rows -> {filepath}")


def filter_team_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only team-level rows (not individual player rows)."""
    return df[df["position"] == "team"].copy()


def filter_top_regions(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to top 5 regions only."""
    mask = df["league"].isin(ALL_TOP_LEAGUE_IDS)
    return df[mask].copy()


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare team-level data for analysis."""
    # Keep only team rows
    df = filter_team_rows(df)

    # Relevant columns for our predictions
    cols_to_keep = [
        # Match identification
        "gameid", "league", "year", "split", "playoffs", "date", "game",
        "patch", "side", "teamname", "result",
        # Game length
        "gamelength",
        # First objectives (binary 1/0)
        "firstblood", "firstdragon", "firstherald", "firstbaron",
        "firsttower", "firstmidtower", "firsttothreetowers",
        # Objective counts
        "dragons", "opp_dragons", "barons", "opp_barons",
        "towers", "opp_towers", "heralds", "opp_heralds",
        "inhibitors", "opp_inhibitors",
        # Combat stats
        "kills", "deaths", "assists",
        # Economy
        "totalgold", "earnedgold",
        "golddiffat10", "xpdiffat10", "csdiffat10",
        "golddiffat15", "xpdiffat15", "csdiffat15",
        "goldat10", "goldat15",
        # Bans/picks
        "ban1", "ban2", "ban3", "ban4", "ban5",
    ]

    # Keep only columns that exist in the data
    available_cols = [c for c in cols_to_keep if c in df.columns]
    df = df[available_cols].copy()

    # Convert date
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Convert numeric columns
    numeric_cols = [
        "gamelength", "result", "firstblood", "firstdragon", "firstherald",
        "firstbaron", "firsttower", "firstmidtower", "firsttothreetowers",
        "dragons", "opp_dragons", "barons", "opp_barons",
        "towers", "opp_towers", "heralds", "opp_heralds",
        "inhibitors", "opp_inhibitors",
        "kills", "deaths", "assists", "totalgold", "earnedgold",
        "golddiffat10", "xpdiffat10", "csdiffat10",
        "golddiffat15", "xpdiffat15", "csdiffat15",
        "goldat10", "goldat15",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort by date
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    return df


def build_series_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build series-level data from game-level data.

    Groups individual games into their BO1/BO3/BO5 series.
    The 'game' column indicates which game within a series (1, 2, 3, etc.).

    Returns DataFrame with one row per series containing:
    - Series winner, total games, score
    - Whether it's BO1, BO3, or BO5
    """
    # Group by gameid to get match pairs (each game has 2 team rows)
    # The gameid should be unique per game, and 'game' column indicates game # in series
    # We need to group by the series identifier

    # Extract series id: gameid without the game number suffix
    # Oracle's Elixir gameid format varies, but games in same series share a prefix
    # The 'game' column tells us game 1, 2, 3 etc. within a series

    # Build series: group by date + teams combination
    series_rows = []

    # Get unique games
    games = df.groupby("gameid").agg({
        "teamname": list,
        "result": list,
        "date": "first",
        "league": "first",
        "game": "first",
        "gamelength": "first",
        "playoffs": "first",
    }).reset_index()

    # For each game, extract the two teams
    for _, row in games.iterrows():
        if len(row["teamname"]) != 2:
            continue
        teams = sorted(row["teamname"])
        series_rows.append({
            "gameid": row["gameid"],
            "date": row["date"],
            "league": row["league"],
            "game_number": row["game"],
            "team1": teams[0],
            "team2": teams[1],
            "gamelength": row["gamelength"],
            "playoffs": row["playoffs"],
            "winner": row["teamname"][row["result"].index(1)]
            if 1 in row["result"] else None,
        })

    if not series_rows:
        return pd.DataFrame()

    series_df = pd.DataFrame(series_rows)
    series_df["date"] = pd.to_datetime(series_df["date"], errors="coerce")

    # Group into series: same date, same teams, same league
    series_df["series_key"] = (
        series_df["date"].dt.date.astype(str) + "_"
        + series_df["team1"] + "_"
        + series_df["team2"] + "_"
        + series_df["league"]
    )

    series_agg = series_df.groupby("series_key").agg({
        "date": "first",
        "league": "first",
        "team1": "first",
        "team2": "first",
        "game_number": "max",
        "winner": list,
        "gamelength": list,
        "playoffs": "first",
    }).reset_index()

    series_agg["total_games"] = series_agg["winner"].apply(len)
    series_agg["series_winner"] = series_agg["winner"].apply(
        lambda wins: max(set(wins), key=wins.count) if wins else None
    )

    # Determine series format
    def get_format(total_games, winners):
        if total_games == 1:
            return "BO1"
        unique_winners = set(w for w in winners if w is not None)
        if len(unique_winners) <= 1 and total_games <= 2:
            return "BO3"
        if total_games <= 3:
            return "BO3"
        return "BO5"

    series_agg["format"] = series_agg.apply(
        lambda r: get_format(r["total_games"], r["winner"]), axis=1
    )

    # Calculate score
    def calc_score(winners, team1, team2):
        t1_wins = sum(1 for w in winners if w == team1)
        t2_wins = sum(1 for w in winners if w == team2)
        return f"{t1_wins}-{t2_wins}"

    series_agg["score"] = series_agg.apply(
        lambda r: calc_score(r["winner"], r["team1"], r["team2"]), axis=1
    )

    return series_agg
