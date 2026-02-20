"""
Feature Engineering - Calculates team statistics and Elo ratings.

Computes rolling averages for each team's performance metrics,
which are then used as features for the prediction models.

Key improvements over basic Elo:
- Recency-weighted stats (exponential decay)
- Patch-aware weighting (recent patches matter more)
- Head-to-head tracking
- Blue/Red side stats
- Variable K-factor (playoffs, international, BO format)
- Playoff vs regular season performance split
"""

import numpy as np
import pandas as pd
from config import (
    ELO_INITIAL, ELO_K_FACTOR, ELO_SEASON_DECAY, ROLLING_WINDOW,
    LEAGUE_TO_REGION, ALL_TOP_LEAGUE_IDS, INTERNATIONAL_TOURNAMENTS,
)


class EloSystem:
    """Elo rating system with variable K-factor."""

    def __init__(self):
        self.ratings: dict[str, float] = {}
        self.game_counts: dict[str, int] = {}
        self.history: list[dict] = []

    def get_rating(self, team: str) -> float:
        if team not in self.ratings:
            self.ratings[team] = ELO_INITIAL
        return self.ratings[team]

    def expected_score(self, team_a: str, team_b: str) -> float:
        """Expected win probability for team_a vs team_b."""
        ra = self.get_rating(team_a)
        rb = self.get_rating(team_b)
        return 1.0 / (1.0 + 10 ** ((rb - ra) / 400))

    def _get_k_factor(self, team: str, league: str, is_playoff: bool) -> float:
        """Dynamic K-factor based on context.

        - New teams (< 30 games): K=40 — ratings converge faster
        - Established teams: K=24 — more stable
        - Playoffs: K * 1.3 — stakes are higher, results matter more
        - International: K * 1.5 — cross-region calibration is rare and valuable
        """
        games = self.game_counts.get(team, 0)

        if games < 30:
            k = 40
        elif games < 60:
            k = ELO_K_FACTOR
        else:
            k = 24

        if is_playoff:
            k *= 1.3
        if league in INTERNATIONAL_TOURNAMENTS:
            k *= 1.5

        return k

    def update(self, winner: str, loser: str, date=None,
               league: str = "", is_playoff: bool = False) -> None:
        """Update ratings after a match result."""
        expected_w = self.expected_score(winner, loser)

        k_w = self._get_k_factor(winner, league, is_playoff)
        k_l = self._get_k_factor(loser, league, is_playoff)
        k = (k_w + k_l) / 2  # average K for the match

        rw = self.get_rating(winner)
        rl = self.get_rating(loser)

        self.ratings[winner] = rw + k * (1.0 - expected_w)
        self.ratings[loser] = rl + k * (0.0 - (1.0 - expected_w))

        self.game_counts[winner] = self.game_counts.get(winner, 0) + 1
        self.game_counts[loser] = self.game_counts.get(loser, 0) + 1

        self.history.append({
            "date": date,
            "winner": winner,
            "loser": loser,
            "winner_elo": self.ratings[winner],
            "loser_elo": self.ratings[loser],
            "league": league,
        })

    def season_reset(self) -> None:
        """Regress all ratings toward the mean at season boundary."""
        for team in self.ratings:
            self.ratings[team] = (
                ELO_INITIAL + (self.ratings[team] - ELO_INITIAL) * ELO_SEASON_DECAY
            )

    def get_top_teams(self, n: int = 20, league_filter: list[str] | None = None,
                      team_league_map: dict[str, str] | None = None) -> list[tuple[str, float]]:
        """Return top N teams by Elo rating."""
        items = list(self.ratings.items())
        if league_filter and team_league_map:
            items = [
                (team, elo) for team, elo in items
                if team_league_map.get(team) in league_filter
            ]
        return sorted(items, key=lambda x: x[1], reverse=True)[:n]


class HeadToHead:
    """Tracks direct matchup history between team pairs."""

    def __init__(self):
        self._records: dict[str, dict] = {}

    @staticmethod
    def _key(team_a: str, team_b: str) -> tuple[str, str]:
        return tuple(sorted([team_a, team_b]))

    def add_result(self, winner: str, loser: str, date=None, patch: str = None):
        key = self._key(winner, loser)
        k = f"{key[0]}|{key[1]}"
        if k not in self._records:
            self._records[k] = {"team1": key[0], "team2": key[1], "games": []}
        self._records[k]["games"].append({
            "winner": winner, "date": date, "patch": patch,
        })

    def get_record(self, team_a: str, team_b: str) -> dict | None:
        """Get head-to-head record between two teams."""
        key = self._key(team_a, team_b)
        k = f"{key[0]}|{key[1]}"
        rec = self._records.get(k)
        if not rec or not rec["games"]:
            return None

        games = rec["games"]
        # Weight recent games more (last 10 meetings)
        recent = games[-10:]
        wins_a = sum(1 for g in recent if g["winner"] == team_a)
        wins_b = len(recent) - wins_a

        total_wins_a = sum(1 for g in games if g["winner"] == team_a)
        total_wins_b = len(games) - total_wins_a

        return {
            "total_games": len(games),
            "total_wins_a": total_wins_a,
            "total_wins_b": total_wins_b,
            "recent_games": len(recent),
            "recent_wins_a": wins_a,
            "recent_wins_b": wins_b,
            "recent_wr_a": wins_a / len(recent) if recent else 0.5,
        }


class TeamStatsTracker:
    """
    Tracks rolling statistics for each team with recency weighting.

    Key features:
    - Exponential decay: recent games weighted exponentially more
    - Patch-aware: games on current patch matter more
    - Separate playoff/regular season tracking
    - Blue/Red side breakdown
    """

    DECAY_LAMBDA = 0.07  # ~14 game half-life

    def __init__(self, window: int = ROLLING_WINDOW):
        self.window = window
        self.team_games: dict[str, list[dict]] = {}

    def add_game(self, team: str, game_stats: dict) -> None:
        """Record a single game's stats for a team."""
        if team not in self.team_games:
            self.team_games[team] = []
        self.team_games[team].append(game_stats)

    def _weighted_avg(self, games: list[dict], key: str,
                      current_patch: str = None) -> float | None:
        """Exponentially-weighted average with patch bonus."""
        vals = []
        weights = []
        n = len(games)
        for i, g in enumerate(games):
            v = g.get(key)
            if v is None:
                continue
            # Exponential decay: most recent game index = n-1
            w = np.exp(-self.DECAY_LAMBDA * (n - 1 - i))
            # Patch bonus: games on same patch get 1.3x weight
            if current_patch and g.get("patch") == current_patch:
                w *= 1.3
            vals.append(v)
            weights.append(w)

        if not vals:
            return None
        return np.average(vals, weights=weights)

    def get_stats(self, team: str, current_patch: str = None) -> dict | None:
        """Get recency-weighted stats for a team."""
        if team not in self.team_games or not self.team_games[team]:
            return None

        all_games = self.team_games[team]
        games = all_games[-self.window:]
        n = len(games)

        def wavg(key):
            return self._weighted_avg(games, key, current_patch)

        # Side-specific win rates
        blue_games = [g for g in games if g.get("is_blue") == 1]
        red_games = [g for g in games if g.get("is_blue") == 0]
        blue_wr = np.mean([g["result"] for g in blue_games]) if blue_games else None
        red_wr = np.mean([g["result"] for g in red_games]) if red_games else None

        # Playoff performance
        playoff_games = [g for g in all_games if g.get("is_playoff")]
        playoff_wr = (np.mean([g["result"] for g in playoff_games[-10:]])
                      if playoff_games else None)

        # Form streak
        streak = 0
        if games:
            last_result = games[-1].get("result")
            for g in reversed(games):
                if g.get("result") == last_result:
                    streak += 1
                else:
                    break
            if last_result == 0:
                streak = -streak

        return {
            "games_played": len(all_games),
            "recent_games": n,
            "win_rate": wavg("result"),
            "avg_gamelength": wavg("gamelength"),
            "first_blood_rate": wavg("firstblood"),
            "first_tower_rate": wavg("firsttower"),
            "first_dragon_rate": wavg("firstdragon"),
            "first_herald_rate": wavg("firstherald"),
            "first_baron_rate": wavg("firstbaron"),
            "first_mid_tower_rate": wavg("firstmidtower"),
            "first_three_towers_rate": wavg("firsttothreetowers"),
            "avg_kills": wavg("kills"),
            "avg_deaths": wavg("deaths"),
            "avg_assists": wavg("assists"),
            "avg_dragons": wavg("dragons"),
            "avg_towers": wavg("towers"),
            "avg_barons": wavg("barons"),
            "avg_heralds": wavg("heralds"),
            "avg_golddiff10": wavg("golddiffat10"),
            "avg_golddiff15": wavg("golddiffat15"),
            "avg_xpdiff10": wavg("xpdiffat10"),
            "avg_xpdiff15": wavg("xpdiffat15"),
            "avg_totalgold": wavg("totalgold"),
            "blue_side_rate": np.mean([g.get("is_blue", 0) for g in games]),
            "blue_wr": blue_wr,
            "red_wr": red_wr,
            "playoff_wr": playoff_wr,
            "streak": streak,
        }


def build_features(df: pd.DataFrame) -> tuple[EloSystem, TeamStatsTracker, HeadToHead, dict[str, str], dict]:
    """
    Process all games chronologically to build:
    1. Elo ratings for all teams (variable K-factor)
    2. Recency-weighted team statistics
    3. Head-to-head records
    4. Data freshness metadata

    Args:
        df: Cleaned team-level DataFrame sorted by date

    Returns:
        (elo_system, stats_tracker, h2h, team_league_map, metadata)
    """
    elo = EloSystem()
    tracker = TeamStatsTracker()
    h2h = HeadToHead()
    team_league_map = {}

    latest_date = None
    latest_patch = None
    total_games = 0

    # Process games in chronological order
    prev_year = None

    for gameid, game_group in df.groupby("gameid", sort=False):
        if len(game_group) != 2:
            continue

        rows = game_group.to_dict("records")
        row_a, row_b = rows[0], rows[1]

        team_a = row_a["teamname"]
        team_b = row_b["teamname"]

        # Season reset at year boundary
        current_year = row_a.get("year")
        if prev_year is not None and current_year != prev_year:
            elo.season_reset()
        prev_year = current_year

        # Track team-league mapping.
        # Prefer domestic leagues (LCK, LEC, etc.) over international tournaments
        league = row_a.get("league", "")
        is_domestic = league in ALL_TOP_LEAGUE_IDS
        for t in (team_a, team_b):
            if is_domestic or t not in team_league_map:
                team_league_map[t] = league

        # Determine winner
        winner = team_a if row_a.get("result") == 1 else team_b
        loser = team_b if winner == team_a else team_a

        # Is this a playoff game?
        is_playoff = bool(row_a.get("playoffs"))
        game_date = row_a.get("date")
        patch = str(row_a.get("patch", "")) if pd.notna(row_a.get("patch")) else None

        # Update Elo with variable K-factor
        elo.update(winner, loser, date=game_date,
                   league=league, is_playoff=is_playoff)

        # Head-to-head
        h2h.add_result(winner, loser, date=game_date, patch=patch)

        # Track stats for both teams
        for row in [row_a, row_b]:
            team = row["teamname"]
            game_stats = {
                "result": row.get("result"),
                "gamelength": row.get("gamelength"),
                "firstblood": row.get("firstblood"),
                "firsttower": row.get("firsttower"),
                "firstdragon": row.get("firstdragon"),
                "firstherald": row.get("firstherald"),
                "firstbaron": row.get("firstbaron"),
                "firstmidtower": row.get("firstmidtower"),
                "firsttothreetowers": row.get("firsttothreetowers"),
                "kills": row.get("kills"),
                "deaths": row.get("deaths"),
                "assists": row.get("assists"),
                "dragons": row.get("dragons"),
                "towers": row.get("towers"),
                "barons": row.get("barons"),
                "heralds": row.get("heralds"),
                "totalgold": row.get("totalgold"),
                "golddiffat10": row.get("golddiffat10"),
                "golddiffat15": row.get("golddiffat15"),
                "xpdiffat10": row.get("xpdiffat10"),
                "xpdiffat15": row.get("xpdiffat15"),
                "is_blue": 1 if row.get("side") == "Blue" else 0,
                "is_playoff": is_playoff,
                "patch": patch,
            }
            tracker.add_game(team, game_stats)

        # Track freshness
        if game_date is not None:
            latest_date = game_date
        if patch:
            latest_patch = patch
        total_games += 1

    metadata = {
        "latest_game_date": str(latest_date) if latest_date else None,
        "latest_patch": latest_patch,
        "total_games": total_games,
        "total_teams": len(team_league_map),
    }

    return elo, tracker, h2h, team_league_map, metadata
