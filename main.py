#!/usr/bin/env python3
"""
LoL Match Predictor - Main entry point.

Predicts League of Legends esports match outcomes based on historical data.

Data source: Oracle's Elixir (https://oracleselixir.com)
Additional reference: gol.gg (https://gol.gg)

Predictions:
  - Match winner (with probability)
  - Map count for BO3/BO5 (score distribution)
  - Game duration (over/under)
  - First tower
  - First dragon
  - First blood
  - First herald

Usage:
  python main.py download
  python main.py predict "T1" "Gen.G" --format BO3
  python main.py rankings --region LCK
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import (
    download_data, load_data, clean_data, filter_top_regions,
    generate_and_save_sample_data, import_csv,
)
from src.features import build_features
from src.predictor import MatchPredictor
from src.display import display_prediction, display_team_rankings, display_help
from config import TOP_REGIONS


def cmd_download(args):
    """Download Oracle's Elixir match data."""
    years = args.years or [2024, 2025, 2026]
    print(f"Downloading Oracle's Elixir data for years: {years}")
    download_data(years, force=args.force)
    print("Done.")


def cmd_generate(args):
    """Generate sample data for testing (simulated matches based on real team stats)."""
    years = args.years or [2024, 2025, 2026]
    print(f"Generating sample match data for years: {years}")
    print("  (Based on real team rosters with simulated statistics)")
    generate_and_save_sample_data(years)
    print("Done. You can now use 'predict', 'rankings', 'teams', 'stats' commands.")


def cmd_import(args):
    """Import a manually downloaded Oracle's Elixir CSV."""
    csv_path = args.csv_path
    year = args.year
    import_csv(csv_path, year)
    print("Done. The data is ready to use.")


def cmd_predict(args):
    """Predict a match outcome."""
    years = args.years or [2024, 2025, 2026]
    team_a = args.team_a
    team_b = args.team_b
    match_format = args.format

    print(f"Loading data for years: {years}...")
    df = load_data(years)
    df = clean_data(df)

    if args.region:
        df = filter_top_regions(df)

    print("Building team features and Elo ratings...")
    elo, tracker, team_league_map = build_features(df)

    predictor = MatchPredictor(elo, tracker, team_league_map)
    prediction = predictor.predict_match(team_a, team_b, match_format)

    print(display_prediction(prediction))


def cmd_rankings(args):
    """Show team Elo rankings."""
    years = args.years or [2024, 2025, 2026]

    print(f"Loading data for years: {years}...")
    df = load_data(years)
    df = clean_data(df)

    print("Building team features and Elo ratings...")
    elo, tracker, team_league_map = build_features(df)

    predictor = MatchPredictor(elo, tracker, team_league_map)

    if args.region:
        title = f"{args.region} Elo Rankings"
        teams = predictor.list_teams(league_filter=args.region)
    else:
        title = "Global Elo Rankings (Top 5 Regions)"
        # Show top from each region
        all_teams = []
        for region_name, league_ids in TOP_REGIONS.items():
            region_teams = elo.get_top_teams(
                n=10, league_filter=league_ids,
                team_league_map=team_league_map
            )
            all_teams.extend(region_teams)
        teams = sorted(all_teams, key=lambda x: x[1], reverse=True)[:30]

    print(display_team_rankings(teams, title))


def cmd_teams(args):
    """List all known teams."""
    years = args.years or [2024, 2025, 2026]

    print(f"Loading data for years: {years}...")
    df = load_data(years)
    df = clean_data(df)

    print("Building team features and Elo ratings...")
    elo, tracker, team_league_map = build_features(df)

    if args.region:
        league_ids = TOP_REGIONS.get(args.region, [args.region])
        teams = {
            t: league for t, league in team_league_map.items()
            if league in league_ids
        }
    else:
        teams = {
            t: league for t, league in team_league_map.items()
            if league in [lid for lids in TOP_REGIONS.values() for lid in lids]
        }

    print(f"\n  Known Teams ({len(teams)}):")
    print("  " + "=" * 45)
    print(f"  {'Team':<30} {'League':>12}")
    print("  " + "-" * 45)

    for team in sorted(teams.keys()):
        elo_val = elo.get_rating(team)
        print(f"  {team:<30} {teams[team]:>12}  (Elo: {elo_val:.0f})")


def cmd_stats(args):
    """Show detailed team stats."""
    years = args.years or [2024, 2025, 2026]
    team_name = args.team

    print(f"Loading data for years: {years}...")
    df = load_data(years)
    df = clean_data(df)

    print("Building team features and Elo ratings...")
    elo, tracker, team_league_map = build_features(df)

    stats = tracker.get_stats(team_name)
    if not stats:
        print(f"\n  Error: No data found for team '{team_name}'")
        print("  Use 'python main.py teams' to see available teams.")
        return

    league = team_league_map.get(team_name, "Unknown")
    elo_rating = elo.get_rating(team_name)

    print(f"\n  Team Stats: {team_name}")
    print(f"  League: {league} | Elo: {elo_rating:.1f}")
    print("  " + "=" * 50)
    print(f"  Total Games:         {stats['games_played']}")
    print(f"  Recent Games Used:   {stats['recent_games']}")
    print(f"  Win Rate:            {stats['win_rate']*100:.1f}%" if stats['win_rate'] is not None else "  Win Rate:            N/A")
    print(f"  Avg Game Length:     {stats['avg_gamelength']/60:.1f} min" if stats['avg_gamelength'] else "  Avg Game Length:     N/A")
    print("  " + "-" * 50)
    print("  First Objectives (rate over recent games):")
    for key, label in [
        ("first_blood_rate", "First Blood"),
        ("first_tower_rate", "First Tower"),
        ("first_dragon_rate", "First Dragon"),
        ("first_herald_rate", "First Herald"),
        ("first_baron_rate", "First Baron"),
    ]:
        val = stats.get(key)
        if val is not None:
            pct = val * 100
            bar = "#" * int(pct / 2)
            print(f"    {label:<20} {pct:>5.1f}% {bar}")
        else:
            print(f"    {label:<20}   N/A")
    print("  " + "-" * 50)
    print("  Combat Stats (avg per game):")
    print(f"    Kills:   {stats['avg_kills']:.1f}" if stats['avg_kills'] is not None else "    Kills:   N/A")
    print(f"    Deaths:  {stats['avg_deaths']:.1f}" if stats['avg_deaths'] is not None else "    Deaths:  N/A")
    print(f"    Assists: {stats['avg_assists']:.1f}" if stats['avg_assists'] is not None else "    Assists: N/A")
    print("  " + "-" * 50)
    print("  Objectives (avg per game):")
    print(f"    Dragons: {stats['avg_dragons']:.1f}" if stats['avg_dragons'] is not None else "    Dragons: N/A")
    print(f"    Towers:  {stats['avg_towers']:.1f}" if stats['avg_towers'] is not None else "    Towers:  N/A")
    print(f"    Barons:  {stats['avg_barons']:.1f}" if stats['avg_barons'] is not None else "    Barons:  N/A")
    print(f"    Heralds: {stats['avg_heralds']:.1f}" if stats['avg_heralds'] is not None else "    Heralds: N/A")
    print("  " + "-" * 50)
    print("  Economy (avg):")
    print(f"    Gold Diff @10min: {stats['avg_golddiff10']:+.0f}" if stats['avg_golddiff10'] is not None else "    Gold Diff @10min: N/A")
    print(f"    Gold Diff @15min: {stats['avg_golddiff15']:+.0f}" if stats['avg_golddiff15'] is not None else "    Gold Diff @15min: N/A")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="LoL Match Predictor - Esports match predictions based on Oracle's Elixir data"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Download command
    dl = subparsers.add_parser("download", help="Download match data from Oracle's Elixir")
    dl.add_argument("--years", type=int, nargs="+", default=None,
                    help="Years to download (default: 2024 2025)")
    dl.add_argument("--force", action="store_true",
                    help="Force re-download")

    # Generate command
    gen = subparsers.add_parser("generate", help="Generate sample data for testing")
    gen.add_argument("--years", type=int, nargs="+", default=None,
                     help="Years to generate (default: 2024 2025 2026)")

    # Import command
    imp = subparsers.add_parser("import", help="Import a manually downloaded CSV")
    imp.add_argument("csv_path", help="Path to the downloaded CSV file")
    imp.add_argument("--year", type=int, default=None,
                     help="Year label (auto-detected from filename if omitted)")

    # Predict command
    pred = subparsers.add_parser("predict", help="Predict match outcome")
    pred.add_argument("team_a", help="First team name")
    pred.add_argument("team_b", help="Second team name")
    pred.add_argument("--format", choices=["BO1", "BO3", "BO5"],
                      default="BO3", help="Match format (default: BO3)")
    pred.add_argument("--years", type=int, nargs="+", default=None)
    pred.add_argument("--region", default=None)

    # Rankings command
    rank = subparsers.add_parser("rankings", help="Show Elo rankings")
    rank.add_argument("--region", default=None,
                      help="Filter by region: LCK, LPL, LEC, LCS, PCS")
    rank.add_argument("--years", type=int, nargs="+", default=None)

    # Teams command
    teams = subparsers.add_parser("teams", help="List known teams")
    teams.add_argument("--region", default=None)
    teams.add_argument("--years", type=int, nargs="+", default=None)

    # Stats command
    st = subparsers.add_parser("stats", help="Show team statistics")
    st.add_argument("team", help="Team name")
    st.add_argument("--years", type=int, nargs="+", default=None)

    args = parser.parse_args()

    if args.command is None:
        print(display_help())
        return

    commands = {
        "download": cmd_download,
        "generate": cmd_generate,
        "import": cmd_import,
        "predict": cmd_predict,
        "rankings": cmd_rankings,
        "teams": cmd_teams,
        "stats": cmd_stats,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
