"""
Prediction Engine - Generates match predictions.

Multi-factor prediction model:
1. Elo rating differential (base probability)
2. Recency-weighted form (momentum)
3. Head-to-head record
4. Early game economy (gold/xp diff at 10/15)
5. Blue/Red side advantage
6. Objective control rates
7. KDA efficiency
8. Streak momentum
9. Playoff experience (for playoff matches)

Each factor adjusts the base Elo probability with calibrated weights.
"""

import numpy as np
from src.features import EloSystem, TeamStatsTracker, HeadToHead


# Factor weights for probability adjustment
WEIGHTS = {
    "form": 0.12,        # Recent win rate differential
    "h2h": 0.08,         # Head-to-head record
    "gold10": 0.07,      # Gold diff at 10 min
    "gold15": 0.05,      # Gold diff at 15 min
    "xp15": 0.04,        # XP diff at 15 min
    "kda": 0.04,         # Kill/death ratio
    "objectives": 0.05,  # First objective rates (tower + dragon + herald)
    "streak": 0.03,      # Win/loss streak momentum
    "side": 0.02,        # Blue/Red side advantage
}


class MatchPredictor:
    """Generates predictions for upcoming LoL esports matches."""

    def __init__(self, elo: EloSystem, tracker: TeamStatsTracker,
                 h2h: HeadToHead, team_league_map: dict[str, str],
                 metadata: dict = None):
        self.elo = elo
        self.tracker = tracker
        self.h2h = h2h
        self.team_league_map = team_league_map
        self.metadata = metadata or {}

    def predict_match(self, team_a: str, team_b: str,
                      match_format: str = "BO3") -> dict:
        """Generate full prediction for a match."""
        current_patch = self.metadata.get("latest_patch")
        stats_a = self.tracker.get_stats(team_a, current_patch=current_patch)
        stats_b = self.tracker.get_stats(team_b, current_patch=current_patch)

        if not stats_a or not stats_b:
            missing = []
            if not stats_a:
                missing.append(team_a)
            if not stats_b:
                missing.append(team_b)
            return {"error": f"No data for: {', '.join(missing)}"}

        # Core win probability (Elo-based)
        elo_prob = self.elo.expected_score(team_a, team_b)

        # Multi-factor adjustment
        adjusted_prob, factors = self._compute_factors(
            team_a, team_b, stats_a, stats_b, elo_prob
        )

        h2h_record = self.h2h.get_record(team_a, team_b)

        result = {
            "team_a": team_a,
            "team_b": team_b,
            "format": match_format,
            "team_a_elo": round(self.elo.get_rating(team_a), 1),
            "team_b_elo": round(self.elo.get_rating(team_b), 1),
            "team_a_stats": self._format_team_stats(stats_a),
            "team_b_stats": self._format_team_stats(stats_b),
            "factors": factors,
            "h2h": self._format_h2h(h2h_record, team_a, team_b),
            "data_patch": current_patch,
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

    def _compute_factors(self, team_a: str, team_b: str,
                         stats_a: dict, stats_b: dict,
                         elo_prob: float) -> tuple[float, list[dict]]:
        """Compute all adjustment factors and return adjusted probability."""
        factors = []
        total_adj = 0.0

        # 1. Recent form (recency-weighted win rate)
        wr_a = stats_a.get("win_rate")
        wr_b = stats_b.get("win_rate")
        if wr_a is not None and wr_b is not None:
            diff = wr_a - wr_b
            adj = diff * WEIGHTS["form"]
            total_adj += adj
            factors.append({
                "name": "Recent Form",
                "team_a_val": f"{wr_a*100:.0f}%",
                "team_b_val": f"{wr_b*100:.0f}%",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # 2. Head-to-head
        h2h_rec = self.h2h.get_record(team_a, team_b)
        if h2h_rec and h2h_rec["recent_games"] >= 2:
            h2h_wr = h2h_rec["recent_wr_a"]
            h2h_diff = h2h_wr - 0.5
            adj = h2h_diff * WEIGHTS["h2h"] * 2
            total_adj += adj
            factors.append({
                "name": "Head-to-Head",
                "team_a_val": f"{h2h_rec['recent_wins_a']}W",
                "team_b_val": f"{h2h_rec['recent_wins_b']}W",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # 3. Gold diff at 10
        gd10_a = stats_a.get("avg_golddiff10")
        gd10_b = stats_b.get("avg_golddiff10")
        if gd10_a is not None and gd10_b is not None:
            diff = (gd10_a - gd10_b) / 4000
            adj = max(-0.15, min(0.15, diff)) * WEIGHTS["gold10"] / 0.15
            total_adj += adj
            factors.append({
                "name": "Gold @ 10min",
                "team_a_val": f"{gd10_a:+.0f}",
                "team_b_val": f"{gd10_b:+.0f}",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # 4. Gold diff at 15
        gd15_a = stats_a.get("avg_golddiff15")
        gd15_b = stats_b.get("avg_golddiff15")
        if gd15_a is not None and gd15_b is not None:
            diff = (gd15_a - gd15_b) / 5000
            adj = max(-0.15, min(0.15, diff)) * WEIGHTS["gold15"] / 0.15
            total_adj += adj
            factors.append({
                "name": "Gold @ 15min",
                "team_a_val": f"{gd15_a:+.0f}",
                "team_b_val": f"{gd15_b:+.0f}",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # 5. XP diff at 15
        xp15_a = stats_a.get("avg_xpdiff15")
        xp15_b = stats_b.get("avg_xpdiff15")
        if xp15_a is not None and xp15_b is not None:
            diff = (xp15_a - xp15_b) / 5000
            adj = max(-0.10, min(0.10, diff)) * WEIGHTS["xp15"] / 0.10
            total_adj += adj

        # 6. KDA
        kills_a = stats_a.get("avg_kills", 0) or 0
        deaths_a = stats_a.get("avg_deaths", 1) or 1
        kills_b = stats_b.get("avg_kills", 0) or 0
        deaths_b = stats_b.get("avg_deaths", 1) or 1
        kd_a = kills_a / max(deaths_a, 0.5)
        kd_b = kills_b / max(deaths_b, 0.5)
        if kd_a + kd_b > 0:
            kd_diff = (kd_a - kd_b) / (kd_a + kd_b)
            adj = kd_diff * WEIGHTS["kda"]
            total_adj += adj
            factors.append({
                "name": "KDA",
                "team_a_val": f"{kd_a:.2f}",
                "team_b_val": f"{kd_b:.2f}",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # 7. Objective control (composite)
        obj_metrics = ["first_tower_rate", "first_dragon_rate", "first_herald_rate"]
        obj_diffs = []
        for m in obj_metrics:
            va = stats_a.get(m)
            vb = stats_b.get(m)
            if va is not None and vb is not None:
                obj_diffs.append(va - vb)
        if obj_diffs:
            avg_obj_diff = np.mean(obj_diffs)
            adj = avg_obj_diff * WEIGHTS["objectives"]
            total_adj += adj
            factors.append({
                "name": "Objectives",
                "team_a_val": f"{np.mean([stats_a.get(m,0) or 0 for m in obj_metrics])*100:.0f}%",
                "team_b_val": f"{np.mean([stats_b.get(m,0) or 0 for m in obj_metrics])*100:.0f}%",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # 8. Streak
        streak_a = stats_a.get("streak", 0)
        streak_b = stats_b.get("streak", 0)
        if streak_a != 0 or streak_b != 0:
            streak_diff = (streak_a - streak_b) / 10
            adj = max(-0.05, min(0.05, streak_diff)) * WEIGHTS["streak"] / 0.05
            total_adj += adj
            factors.append({
                "name": "Streak",
                "team_a_val": f"{streak_a:+d}",
                "team_b_val": f"{streak_b:+d}",
                "impact": round(adj * 100, 1),
                "favors": team_a if adj > 0 else team_b if adj < 0 else "neutral",
            })

        # Apply adjustments
        adjusted = elo_prob + total_adj
        adjusted = max(0.03, min(0.97, adjusted))

        return adjusted, factors

    def _predict_winner(self, team_a: str, team_b: str,
                        win_prob: float) -> dict:
        """Predict match winner with confidence."""
        if win_prob >= 0.5:
            predicted_winner = team_a
            confidence = win_prob
        else:
            predicted_winner = team_b
            confidence = 1 - win_prob

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
        """Predict score line distribution for BO3/BO5."""
        p = win_prob

        if match_format == "BO3":
            scores = self._bo3_probabilities(p)
        else:
            scores = self._bo5_probabilities(p)

        best_score = max(scores, key=lambda x: x["probability"])

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
        q = 1 - p
        return [
            {"score": "2-0", "probability": p * p, "total_games": 2, "winner": "team_a"},
            {"score": "2-1", "probability": 2 * p * q * p, "total_games": 3, "winner": "team_a"},
            {"score": "0-2", "probability": q * q, "total_games": 2, "winner": "team_b"},
            {"score": "1-2", "probability": 2 * p * q * q, "total_games": 3, "winner": "team_b"},
        ]

    def _bo5_probabilities(self, p: float) -> list[dict]:
        q = 1 - p
        return [
            {"score": "3-0", "probability": p**3, "total_games": 3, "winner": "team_a"},
            {"score": "3-1", "probability": 3 * (p**3) * q, "total_games": 4, "winner": "team_a"},
            {"score": "3-2", "probability": 6 * (p**3) * (q**2), "total_games": 5, "winner": "team_a"},
            {"score": "0-3", "probability": q**3, "total_games": 3, "winner": "team_b"},
            {"score": "1-3", "probability": 3 * (q**3) * p, "total_games": 4, "winner": "team_b"},
            {"score": "2-3", "probability": 6 * (q**3) * (p**2), "total_games": 5, "winner": "team_b"},
        ]

    def _predict_duration(self, stats_a: dict, stats_b: dict) -> dict:
        """Predict game duration based on team averages."""
        dur_a = stats_a.get("avg_gamelength")
        dur_b = stats_b.get("avg_gamelength")

        if dur_a is None or dur_b is None:
            return {"error": "Insufficient game duration data"}

        predicted_seconds = (dur_a + dur_b) / 2
        predicted_minutes = predicted_seconds / 60

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
        std_dev = 4.5
        z = (threshold - predicted) / std_dev
        prob_under = 1.0 / (1.0 + np.exp(-1.7 * z))
        return 1.0 - prob_under

    def _predict_first_objective(self, team_a: str, team_b: str,
                                 stats_a: dict, stats_b: dict,
                                 rate_key: str) -> dict:
        """Predict which team takes an objective first."""
        rate_a = stats_a.get(rate_key)
        rate_b = stats_b.get(rate_key)

        objective_name = rate_key.replace("_rate", "").replace("first_", "")

        if rate_a is None or rate_b is None:
            return {"error": f"Insufficient {objective_name} data"}

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

    def _format_h2h(self, record: dict | None,
                    team_a: str, team_b: str) -> dict | None:
        """Format head-to-head for display."""
        if not record:
            return None
        return {
            "total_games": record["total_games"],
            "team_a_wins": record["total_wins_a"],
            "team_b_wins": record["total_wins_b"],
            "recent_games": record["recent_games"],
            "recent_a_wins": record["recent_wins_a"],
            "recent_b_wins": record["recent_wins_b"],
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
            "streak": stats.get("streak", 0),
            "blue_wr": f"{stats['blue_wr']*100:.0f}%" if stats.get("blue_wr") is not None else "N/A",
            "red_wr": f"{stats['red_wr']*100:.0f}%" if stats.get("red_wr") is not None else "N/A",
            "playoff_wr": f"{stats['playoff_wr']*100:.0f}%" if stats.get("playoff_wr") is not None else "N/A",
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
