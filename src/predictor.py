"""
Prediction Engine - Generates match predictions.

Prediction types:
1. Match Winner - Elo + team stats based probability
2. Map Count (BO3/BO5) - Score line distribution from win probability
3. Game Duration - Weighted average of team game lengths
4. First Tower - Comparative first tower rates
5. First Dragon - Comparative first dragon rates
"""

import numpy as np
from src.features import EloSystem, TeamStatsTracker


class MatchPredictor:
    """Generates predictions for upcoming LoL esports matches."""

    def __init__(self, elo: EloSystem, tracker: TeamStatsTracker,
                 team_league_map: dict[str, str]):
        self.elo = elo
        self.tracker = tracker
        self.team_league_map = team_league_map

    def predict_match(self, team_a: str, team_b: str,
                      match_format: str = "BO3") -> dict:
        """
        Generate full prediction for a match.

        Args:
            team_a: First team name
            team_b: Second team name
            match_format: "BO1", "BO3", or "BO5"

        Returns:
            Dictionary with all predictions
        """
        stats_a = self.tracker.get_stats(team_a)
        stats_b = self.tracker.get_stats(team_b)

        if not stats_a or not stats_b:
            missing = []
            if not stats_a:
                missing.append(team_a)
            if not stats_b:
                missing.append(team_b)
            return {"error": f"No data for: {', '.join(missing)}"}

        # Core win probability (Elo-based)
        elo_prob = self.elo.expected_score(team_a, team_b)

        # Adjust with team stats
        adjusted_prob = self._adjust_win_probability(elo_prob, stats_a, stats_b)

        result = {
            "team_a": team_a,
            "team_b": team_b,
            "format": match_format,
            "team_a_elo": round(self.elo.get_rating(team_a), 1),
            "team_b_elo": round(self.elo.get_rating(team_b), 1),
            "team_a_stats": self._format_team_stats(stats_a),
            "team_b_stats": self._format_team_stats(stats_b),
        }

        # 1. Match Winner
        result["winner_prediction"] = self._predict_winner(
            team_a, team_b, adjusted_prob
        )

        # 2. Map Count (for BO3/BO5)
        if match_format in ("BO3", "BO5"):
            result["map_count"] = self._predict_map_count(
                team_a, team_b, adjusted_prob, match_format
            )

        # 3. Game Duration
        result["game_duration"] = self._predict_duration(stats_a, stats_b)

        # 4. First Tower
        result["first_tower"] = self._predict_first_objective(
            team_a, team_b, stats_a, stats_b, "first_tower_rate"
        )

        # 5. First Dragon
        result["first_dragon"] = self._predict_first_objective(
            team_a, team_b, stats_a, stats_b, "first_dragon_rate"
        )

        # 6. First Blood
        result["first_blood"] = self._predict_first_objective(
            team_a, team_b, stats_a, stats_b, "first_blood_rate"
        )

        # 7. First Herald
        result["first_herald"] = self._predict_first_objective(
            team_a, team_b, stats_a, stats_b, "first_herald_rate"
        )

        return result

    def _adjust_win_probability(self, elo_prob: float,
                                stats_a: dict, stats_b: dict) -> float:
        """
        Adjust Elo-based probability using recent performance stats.

        Factors considered:
        - Recent win rate (momentum)
        - Gold differential at 10/15 min (early game strength)
        - Kill/death ratio
        """
        adjustments = []

        # Recent form adjustment
        wr_a = stats_a.get("win_rate")
        wr_b = stats_b.get("win_rate")
        if wr_a is not None and wr_b is not None:
            form_diff = (wr_a - wr_b) * 0.15
            adjustments.append(form_diff)

        # Early game gold diff adjustment
        gd10_a = stats_a.get("avg_golddiff10")
        gd10_b = stats_b.get("avg_golddiff10")
        if gd10_a is not None and gd10_b is not None:
            # Normalize gold diff (typical range: -2000 to +2000)
            gold_factor = (gd10_a - gd10_b) / 4000
            gold_factor = max(-0.1, min(0.1, gold_factor))
            adjustments.append(gold_factor)

        # KDA-based adjustment
        kills_a = stats_a.get("avg_kills", 0) or 0
        deaths_a = stats_a.get("avg_deaths", 1) or 1
        kills_b = stats_b.get("avg_kills", 0) or 0
        deaths_b = stats_b.get("avg_deaths", 1) or 1

        kd_a = kills_a / max(deaths_a, 1)
        kd_b = kills_b / max(deaths_b, 1)
        if kd_a + kd_b > 0:
            kd_factor = (kd_a - kd_b) / (kd_a + kd_b) * 0.05
            adjustments.append(kd_factor)

        # Apply adjustments
        total_adj = sum(adjustments)
        adjusted = elo_prob + total_adj
        return max(0.05, min(0.95, adjusted))

    def _predict_winner(self, team_a: str, team_b: str,
                        win_prob: float) -> dict:
        """Predict match winner with confidence."""
        if win_prob >= 0.5:
            predicted_winner = team_a
            confidence = win_prob
        else:
            predicted_winner = team_b
            confidence = 1 - win_prob

        # Confidence tier
        if confidence >= 0.75:
            tier = "HIGH"
        elif confidence >= 0.60:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return {
            "predicted_winner": predicted_winner,
            "team_a_win_prob": round(win_prob * 100, 1),
            "team_b_win_prob": round((1 - win_prob) * 100, 1),
            "confidence": tier,
        }

    def _predict_map_count(self, team_a: str, team_b: str,
                           win_prob: float, match_format: str) -> dict:
        """
        Predict score line distribution for BO3/BO5.

        Uses binomial model:
        - For BO3: possible scores are 2-0, 2-1, 0-2, 1-2
        - For BO5: possible scores are 3-0, 3-1, 3-2, 0-3, 1-3, 2-3
        """
        p = win_prob  # team_a single-game win probability

        if match_format == "BO3":
            scores = self._bo3_probabilities(p)
        else:
            scores = self._bo5_probabilities(p)

        # Find most likely outcome
        best_score = max(scores, key=lambda x: x["probability"])

        # Total games distribution
        total_games_dist = {}
        for score_info in scores:
            total = score_info["total_games"]
            if total not in total_games_dist:
                total_games_dist[total] = 0
            total_games_dist[total] += score_info["probability"]

        return {
            "most_likely_score": best_score["score"],
            "most_likely_prob": round(best_score["probability"] * 100, 1),
            "all_scores": [
                {
                    "score": s["score"],
                    "probability": round(s["probability"] * 100, 1),
                }
                for s in sorted(scores, key=lambda x: -x["probability"])
            ],
            "total_games_distribution": {
                str(k): round(v * 100, 1)
                for k, v in sorted(total_games_dist.items())
            },
        }

    def _bo3_probabilities(self, p: float) -> list[dict]:
        """Calculate BO3 score probabilities."""
        q = 1 - p
        return [
            {"score": "2-0", "probability": p * p, "total_games": 2,
             "winner": "team_a"},
            {"score": "2-1", "probability": 2 * p * q * p, "total_games": 3,
             "winner": "team_a"},
            {"score": "0-2", "probability": q * q, "total_games": 2,
             "winner": "team_b"},
            {"score": "1-2", "probability": 2 * p * q * q, "total_games": 3,
             "winner": "team_b"},
        ]

    def _bo5_probabilities(self, p: float) -> list[dict]:
        """Calculate BO5 score probabilities."""
        q = 1 - p
        return [
            {"score": "3-0", "probability": p ** 3, "total_games": 3,
             "winner": "team_a"},
            {"score": "3-1", "probability": 3 * (p ** 3) * q, "total_games": 4,
             "winner": "team_a"},
            {"score": "3-2", "probability": 6 * (p ** 3) * (q ** 2), "total_games": 5,
             "winner": "team_a"},
            {"score": "0-3", "probability": q ** 3, "total_games": 3,
             "winner": "team_b"},
            {"score": "1-3", "probability": 3 * (q ** 3) * p, "total_games": 4,
             "winner": "team_b"},
            {"score": "2-3", "probability": 6 * (q ** 3) * (p ** 2), "total_games": 5,
             "winner": "team_b"},
        ]

    def _predict_duration(self, stats_a: dict, stats_b: dict) -> dict:
        """
        Predict game duration based on team averages.

        Shorter games indicate more aggressive/dominant teams.
        """
        dur_a = stats_a.get("avg_gamelength")
        dur_b = stats_b.get("avg_gamelength")

        if dur_a is None or dur_b is None:
            return {"error": "Insufficient game duration data"}

        # Weighted average of both teams' average game lengths
        predicted_seconds = (dur_a + dur_b) / 2
        predicted_minutes = predicted_seconds / 60

        # Standard thresholds for over/under
        thresholds = [25.5, 28.5, 30.5, 32.5]
        over_under = {}
        for threshold in thresholds:
            prob_over = self._duration_over_probability(
                predicted_minutes, threshold, stats_a, stats_b
            )
            over_under[f"{threshold}"] = {
                "over_prob": round(prob_over * 100, 1),
                "under_prob": round((1 - prob_over) * 100, 1),
            }

        return {
            "predicted_minutes": round(predicted_minutes, 1),
            "predicted_seconds": round(predicted_seconds),
            "team_a_avg_minutes": round(dur_a / 60, 1) if dur_a else None,
            "team_b_avg_minutes": round(dur_b / 60, 1) if dur_b else None,
            "over_under": over_under,
        }

    def _duration_over_probability(self, predicted: float, threshold: float,
                                   stats_a: dict, stats_b: dict) -> float:
        """Estimate probability of game going over threshold minutes."""
        # Use a simple logistic approach based on how far prediction is from threshold
        # Standard deviation of game length is typically ~5 minutes in pro play
        std_dev = 4.5
        z = (threshold - predicted) / std_dev
        # Cumulative distribution approximation
        prob_under = 1.0 / (1.0 + np.exp(-1.7 * z))
        return 1.0 - prob_under

    def _predict_first_objective(self, team_a: str, team_b: str,
                                 stats_a: dict, stats_b: dict,
                                 rate_key: str) -> dict:
        """
        Predict which team takes an objective first.

        Uses comparative rates: if team A gets first tower 60% of the time
        and team B gets it 40%, the prediction adjusts accordingly.
        """
        rate_a = stats_a.get(rate_key)
        rate_b = stats_b.get(rate_key)

        objective_name = rate_key.replace("_rate", "").replace("first_", "")

        if rate_a is None or rate_b is None:
            return {"error": f"Insufficient {objective_name} data"}

        # Normalize rates against each other
        total = rate_a + rate_b
        if total == 0:
            prob_a = 0.5
        else:
            prob_a = rate_a / total

        if prob_a >= 0.5:
            predicted = team_a
            confidence_pct = prob_a
        else:
            predicted = team_b
            confidence_pct = 1 - prob_a

        return {
            "objective": objective_name.replace("_", " ").title(),
            "predicted_team": predicted,
            "team_a_prob": round(prob_a * 100, 1),
            "team_b_prob": round((1 - prob_a) * 100, 1),
            "team_a_rate": round(rate_a * 100, 1) if rate_a else 0,
            "team_b_rate": round(rate_b * 100, 1) if rate_b else 0,
        }

    def _format_team_stats(self, stats: dict) -> dict:
        """Format team stats for display."""
        return {
            "games_played": stats.get("games_played", 0),
            "recent_games": stats.get("recent_games", 0),
            "win_rate": f"{stats['win_rate']*100:.1f}%" if stats.get("win_rate") is not None else "N/A",
            "avg_game_min": f"{stats['avg_gamelength']/60:.1f}" if stats.get("avg_gamelength") else "N/A",
            "first_tower": f"{stats['first_tower_rate']*100:.0f}%" if stats.get("first_tower_rate") is not None else "N/A",
            "first_dragon": f"{stats['first_dragon_rate']*100:.0f}%" if stats.get("first_dragon_rate") is not None else "N/A",
            "first_blood": f"{stats['first_blood_rate']*100:.0f}%" if stats.get("first_blood_rate") is not None else "N/A",
            "first_herald": f"{stats['first_herald_rate']*100:.0f}%" if stats.get("first_herald_rate") is not None else "N/A",
            "avg_kills": f"{stats['avg_kills']:.1f}" if stats.get("avg_kills") is not None else "N/A",
            "avg_deaths": f"{stats['avg_deaths']:.1f}" if stats.get("avg_deaths") is not None else "N/A",
            "gold_diff_10": f"{stats['avg_golddiff10']:+.0f}" if stats.get("avg_golddiff10") is not None else "N/A",
            "gold_diff_15": f"{stats['avg_golddiff15']:+.0f}" if stats.get("avg_golddiff15") is not None else "N/A",
        }

    def list_teams(self, league_filter: str | None = None) -> list[tuple[str, float]]:
        """List all known teams with their Elo ratings."""
        if league_filter:
            from config import TOP_REGIONS
            league_ids = TOP_REGIONS.get(league_filter, [league_filter])
            return self.elo.get_top_teams(
                n=50, league_filter=league_ids,
                team_league_map=self.team_league_map
            )
        return self.elo.get_top_teams(n=50)
