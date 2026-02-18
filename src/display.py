"""
Display module - Formats prediction output for terminal.
"""


def display_prediction(pred: dict) -> str:
    """Format a full match prediction for terminal display."""
    if "error" in pred:
        return f"Error: {pred['error']}"

    lines = []
    team_a = pred["team_a"]
    team_b = pred["team_b"]

    # Header
    lines.append("=" * 70)
    lines.append(f"  MATCH PREDICTION: {team_a} vs {team_b}")
    lines.append(f"  Format: {pred['format']}")
    lines.append("=" * 70)

    # Elo ratings
    lines.append("")
    lines.append(f"  Elo Ratings: {team_a} [{pred['team_a_elo']}] vs "
                 f"{team_b} [{pred['team_b_elo']}]")

    # Team stats comparison
    lines.append("")
    lines.append("  TEAM STATISTICS (recent games)")
    lines.append("  " + "-" * 50)
    sa = pred["team_a_stats"]
    sb = pred["team_b_stats"]

    stat_rows = [
        ("Games Played", sa["games_played"], sb["games_played"]),
        ("Win Rate", sa["win_rate"], sb["win_rate"]),
        ("Avg Game (min)", sa["avg_game_min"], sb["avg_game_min"]),
        ("First Tower %", sa["first_tower"], sb["first_tower"]),
        ("First Dragon %", sa["first_dragon"], sb["first_dragon"]),
        ("First Blood %", sa["first_blood"], sb["first_blood"]),
        ("First Herald %", sa["first_herald"], sb["first_herald"]),
        ("Avg Kills", sa["avg_kills"], sb["avg_kills"]),
        ("Avg Deaths", sa["avg_deaths"], sb["avg_deaths"]),
        ("Gold Diff @10", sa["gold_diff_10"], sb["gold_diff_10"]),
        ("Gold Diff @15", sa["gold_diff_15"], sb["gold_diff_15"]),
    ]

    lines.append(f"  {'Stat':<20} {team_a:>15} {team_b:>15}")
    lines.append("  " + "-" * 50)
    for name, val_a, val_b in stat_rows:
        lines.append(f"  {name:<20} {str(val_a):>15} {str(val_b):>15}")

    # Winner prediction
    wp = pred["winner_prediction"]
    lines.append("")
    lines.append("  MATCH WINNER")
    lines.append("  " + "-" * 50)
    lines.append(f"  Prediction: {wp['predicted_winner']} "
                 f"(confidence: {wp['confidence']})")
    lines.append(f"  {team_a}: {wp['team_a_win_prob']}% | "
                 f"{team_b}: {wp['team_b_win_prob']}%")

    # Map count (BO3/BO5)
    if "map_count" in pred:
        mc = pred["map_count"]
        lines.append("")
        lines.append(f"  MAP COUNT ({pred['format']})")
        lines.append("  " + "-" * 50)
        lines.append(f"  Most likely score: {mc['most_likely_score']} "
                     f"({mc['most_likely_prob']}%)")
        lines.append("")
        lines.append("  Score probabilities:")
        for score_info in mc["all_scores"]:
            bar_len = int(score_info["probability"] / 2)
            bar = "#" * bar_len
            lines.append(f"    {score_info['score']:>5}: "
                         f"{score_info['probability']:>5.1f}% {bar}")
        lines.append("")
        lines.append("  Total games distribution:")
        for games, prob in mc["total_games_distribution"].items():
            bar_len = int(prob / 2)
            bar = "#" * bar_len
            lines.append(f"    {games} games: {prob:>5.1f}% {bar}")

    # Game Duration
    gd = pred.get("game_duration", {})
    if "error" not in gd:
        lines.append("")
        lines.append("  GAME DURATION")
        lines.append("  " + "-" * 50)
        lines.append(f"  Predicted: ~{gd['predicted_minutes']} minutes "
                     f"({gd['predicted_seconds']} sec)")
        lines.append(f"  {team_a} avg: {gd['team_a_avg_minutes']} min | "
                     f"{team_b} avg: {gd['team_b_avg_minutes']} min")
        lines.append("")
        lines.append("  Over/Under lines:")
        for threshold, ou in gd.get("over_under", {}).items():
            lines.append(f"    {threshold} min: "
                         f"Over {ou['over_prob']}% | Under {ou['under_prob']}%")

    # First objectives
    for obj_key in ["first_tower", "first_dragon", "first_blood", "first_herald"]:
        obj = pred.get(obj_key, {})
        if "error" not in obj:
            lines.append("")
            lines.append(f"  FIRST {obj['objective'].upper()}")
            lines.append("  " + "-" * 50)
            lines.append(f"  Prediction: {obj['predicted_team']}")
            lines.append(f"  {team_a}: {obj['team_a_prob']}% "
                         f"(rate: {obj['team_a_rate']}%) | "
                         f"{team_b}: {obj['team_b_prob']}% "
                         f"(rate: {obj['team_b_rate']}%)")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def display_team_rankings(teams: list[tuple[str, float]],
                          title: str = "Team Rankings") -> str:
    """Format team Elo rankings for display."""
    lines = []
    lines.append(f"\n  {title}")
    lines.append("  " + "=" * 40)
    lines.append(f"  {'#':<4} {'Team':<25} {'Elo':>8}")
    lines.append("  " + "-" * 40)

    for i, (team, elo) in enumerate(teams, 1):
        lines.append(f"  {i:<4} {team:<25} {elo:>8.1f}")

    return "\n".join(lines)


def display_help() -> str:
    """Display usage help."""
    return """
  LoL Match Predictor - Usage
  ===========================

  Commands:
    python main.py download          Download match data (2024-2025)
    python main.py download --years 2023 2024 2025
                                     Download specific years
    python main.py download --force  Re-download existing files

    python main.py predict "T1" "Gen.G" --format BO3
                                     Predict a match result
    python main.py predict "T1" "Gen.G" --format BO5
                                     Predict a BO5 series

    python main.py rankings          Show global Elo rankings
    python main.py rankings --region LCK
                                     Show rankings for a region

    python main.py teams             List all known teams
    python main.py teams --region LPL
                                     List teams in a region

    python main.py stats "T1"        Show detailed team stats

  Options:
    --years YEAR [YEAR ...]    Years to load (default: 2024 2025)
    --format BO1|BO3|BO5       Match format (default: BO3)
    --region REGION            Filter by region: LCK, LPL, LEC, LCS, PCS
    --force                    Force re-download of data

  Data Source:
    Oracle's Elixir (https://oracleselixir.com)
    Free professional LoL esports match data, updated daily.

  Supplementary Sources:
    gol.gg (https://gol.gg) - Detailed tournament/team stats
    Leaguepedia (https://lol.fandom.com) - Wiki with match data
"""
