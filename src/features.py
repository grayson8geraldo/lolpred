"""
Feature Engineering - Calculates team statistics and Elo ratings.

Computes rolling averages for each team's performance metrics,
which are then used as features for the prediction models.
"""

import numpy as np
import pandas as pd
from config import (
    ELO_INITIAL, ELO_K_FACTOR, ELO_SEASON_DECAY, ROLLING_WINDOW
)


class EloSystem:
    """Elo rating system for teams."""

    def __init__(self):
        self.ratings: dict[str, float] = {}
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

    def update(self, winner: str, loser: str, date=None) -> None:
        """Update ratings after a match result."""
        expected_w = self.expected_score(winner, loser)
        expected_l = 1.0 - expected_w

        rw = self.get_rating(winner)
        rl = self.get_rating(loser)

        self.ratings[winner] = rw + ELO_K_FACTOR * (1.0 - expected_w)
        self.ratings[loser] = rl + ELO_K_FACTOR * (0.0 - expected_l)

        self.history.append({
            "date": date,
            "winner": winner,
            "loser": loser,
            "winner_elo": self.ratings[winner],
            "loser_elo": self.ratings[loser],
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


class TeamStatsTracker:
    """
    Tracks rolling statistics for each team.

    Computes rolling averages over the last N games for:
    - Win rate
    - Game duration
    - First tower / first dragon / first blood / first herald / first baron rates
    - Kill/death stats
    - Gold differential at 10/15 min
    - Objective control (dragons, towers, barons)
    """

    def __init__(self, window: int = ROLLING_WINDOW):
        self.window = window
        self.team_games: dict[str, list[dict]] = {}

    def add_game(self, team: str, game_stats: dict) -> None:
        """Record a single game's stats for a team."""
        if team not in self.team_games:
            self.team_games[team] = []
        self.team_games[team].append(game_stats)

    def get_stats(self, team: str) -> dict | None:
        """Get rolling average stats for a team."""
        if team not in self.team_games or not self.team_games[team]:
            return None

        games = self.team_games[team][-self.window:]
        n = len(games)

        def avg(key):
            vals = [g.get(key) for g in games if g.get(key) is not None]
            return np.mean(vals) if vals else None

        def rate(key):
            vals = [g.get(key) for g in games if g.get(key) is not None]
            return np.mean(vals) if vals else None

        return {
            "games_played": len(self.team_games[team]),
            "recent_games": n,
            "win_rate": rate("result"),
            "avg_gamelength": avg("gamelength"),
            "first_blood_rate": rate("firstblood"),
            "first_tower_rate": rate("firsttower"),
            "first_dragon_rate": rate("firstdragon"),
            "first_herald_rate": rate("firstherald"),
            "first_baron_rate": rate("firstbaron"),
            "first_mid_tower_rate": rate("firstmidtower"),
            "first_three_towers_rate": rate("firsttothreetowers"),
            "avg_kills": avg("kills"),
            "avg_deaths": avg("deaths"),
            "avg_assists": avg("assists"),
            "avg_dragons": avg("dragons"),
            "avg_towers": avg("towers"),
            "avg_barons": avg("barons"),
            "avg_heralds": avg("heralds"),
            "avg_golddiff10": avg("golddiffat10"),
            "avg_golddiff15": avg("golddiffat15"),
            "avg_xpdiff10": avg("xpdiffat10"),
            "avg_xpdiff15": avg("xpdiffat15"),
            "avg_totalgold": avg("totalgold"),
            "blue_side_rate": rate("is_blue"),
        }


def build_features(df: pd.DataFrame) -> tuple[EloSystem, TeamStatsTracker, dict[str, str]]:
    """
    Process all games chronologically to build:
    1. Elo ratings for all teams
    2. Rolling team statistics

    Args:
        df: Cleaned team-level DataFrame sorted by date

    Returns:
        (elo_system, stats_tracker, team_league_map)
    """
    elo = EloSystem()
    tracker = TeamStatsTracker()
    team_league_map = {}

    # Process games in chronological order
    # Each game has exactly 2 team rows (one per side)
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

        # Track team-league mapping
        league = row_a.get("league", "")
        team_league_map[team_a] = league
        team_league_map[team_b] = league

        # Determine winner
        winner = team_a if row_a.get("result") == 1 else team_b
        loser = team_b if winner == team_a else team_a

        # Update Elo
        elo.update(winner, loser, date=row_a.get("date"))

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
            }
            tracker.add_game(team, game_stats)

    return elo, tracker, team_league_map
