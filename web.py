#!/usr/bin/env python3
"""
LoL Match Predictor - Web Application (Flask).

Run: python web.py
Open: http://localhost:5000
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from src.data_loader import load_data, clean_data, download_data
from src.features import build_features
from src.predictor import MatchPredictor
from config import TOP_REGIONS, DATA_DIR

app = Flask(__name__)

# Global state: loaded once, reused across requests
_predictor = None
_elo = None
_tracker = None
_team_league_map = None
_all_teams = []


def _ensure_data(years):
    """Download real data from Oracle's Elixir if CSV files are missing."""
    os.makedirs(DATA_DIR, exist_ok=True)
    missing = [
        y for y in years
        if not os.path.isfile(os.path.join(DATA_DIR, f"{y}_matches.csv"))
    ]
    if missing:
        print(f"Missing data for years: {missing}. Downloading from Oracle's Elixir...")
        download_data(missing)


_load_error = None


def _load_predictor(years=None):
    """Load data and build predictor (cached globally)."""
    global _predictor, _elo, _tracker, _team_league_map, _all_teams, _load_error

    if _predictor is not None:
        return True

    if _load_error is not None:
        return False

    if years is None:
        years = [2024, 2025, 2026]

    _ensure_data(years)

    try:
        print("Loading data...")
        df = load_data(years)
    except FileNotFoundError as e:
        _load_error = str(e)
        print(f"ERROR: {_load_error}")
        return False

    df = clean_data(df)

    print("Building Elo ratings and team stats...")
    _elo, _tracker, _team_league_map = build_features(df)
    _predictor = MatchPredictor(_elo, _tracker, _team_league_map)

    # Build sorted team list
    top_league_ids = [lid for lids in TOP_REGIONS.values() for lid in lids]
    _all_teams = sorted([
        {
            "name": team,
            "league": league,
            "elo": round(_elo.get_rating(team), 1),
        }
        for team, league in _team_league_map.items()
        if league in top_league_ids
    ], key=lambda t: t["name"])

    print(f"Loaded {len(_all_teams)} teams. Server ready.")
    return True


def _nodata():
    """Return the 'no data' error page."""
    return render_template("nodata.html"), 503


@app.route("/")
def index():
    """Main page with prediction form."""
    if not _load_predictor():
        return _nodata()
    regions = list(TOP_REGIONS.keys())
    return render_template("index.html", teams=_all_teams, regions=regions)


@app.route("/predict", methods=["POST"])
def predict():
    """Handle prediction request."""
    if not _load_predictor():
        return _nodata()

    team_a = request.form.get("team_a", "").strip()
    team_b = request.form.get("team_b", "").strip()
    match_format = request.form.get("format", "BO3")

    if not team_a or not team_b:
        return render_template("index.html", teams=_all_teams,
                               regions=list(TOP_REGIONS.keys()),
                               error="Select both teams")

    if team_a == team_b:
        return render_template("index.html", teams=_all_teams,
                               regions=list(TOP_REGIONS.keys()),
                               error="Teams must be different")

    prediction = _predictor.predict_match(team_a, team_b, match_format)

    if "error" in prediction:
        return render_template("index.html", teams=_all_teams,
                               regions=list(TOP_REGIONS.keys()),
                               error=prediction["error"])

    return render_template("result.html", pred=prediction)


@app.route("/rankings")
def rankings():
    """Rankings page."""
    if not _load_predictor():
        return _nodata()

    region = request.args.get("region", "")
    rankings_data = []

    if region and region in TOP_REGIONS:
        league_ids = TOP_REGIONS[region]
        teams = _elo.get_top_teams(
            n=50, league_filter=league_ids,
            team_league_map=_team_league_map
        )
        title = f"{region} Rankings"
    else:
        all_teams = []
        for region_name, league_ids in TOP_REGIONS.items():
            region_teams = _elo.get_top_teams(
                n=10, league_filter=league_ids,
                team_league_map=_team_league_map
            )
            all_teams.extend(region_teams)
        teams = sorted(all_teams, key=lambda x: x[1], reverse=True)[:30]
        title = "Global Rankings"
        region = ""

    for i, (team, elo) in enumerate(teams, 1):
        league = _team_league_map.get(team, "")
        stats = _tracker.get_stats(team)
        rankings_data.append({
            "rank": i,
            "team": team,
            "league": league,
            "elo": round(elo, 1),
            "win_rate": f"{stats['win_rate']*100:.0f}%" if stats and stats.get("win_rate") is not None else "N/A",
            "games": stats["games_played"] if stats else 0,
        })

    return render_template("rankings.html", rankings=rankings_data,
                           title=title, regions=list(TOP_REGIONS.keys()),
                           selected_region=region)


@app.route("/team/<team_name>")
def team_stats(team_name):
    """Team detail page."""
    if not _load_predictor():
        return _nodata()

    stats = _tracker.get_stats(team_name)
    if not stats:
        return render_template("team.html", error=f"Team '{team_name}' not found",
                               team_name=team_name)

    league = _team_league_map.get(team_name, "Unknown")
    elo = round(_elo.get_rating(team_name), 1)

    def pct(val):
        return round(val * 100, 1) if val is not None else None

    def rnd(val, digits=1):
        return round(val, digits) if val is not None else None

    team_data = {
        "name": team_name,
        "league": league,
        "elo": elo,
        "games_played": stats["games_played"],
        "recent_games": stats["recent_games"],
        "win_rate": pct(stats.get("win_rate")),
        "avg_gamelength_min": rnd(stats["avg_gamelength"] / 60) if stats.get("avg_gamelength") else None,
        "first_blood": pct(stats.get("first_blood_rate")),
        "first_tower": pct(stats.get("first_tower_rate")),
        "first_dragon": pct(stats.get("first_dragon_rate")),
        "first_herald": pct(stats.get("first_herald_rate")),
        "first_baron": pct(stats.get("first_baron_rate")),
        "avg_kills": rnd(stats.get("avg_kills")),
        "avg_deaths": rnd(stats.get("avg_deaths")),
        "avg_assists": rnd(stats.get("avg_assists")),
        "avg_dragons": rnd(stats.get("avg_dragons")),
        "avg_towers": rnd(stats.get("avg_towers")),
        "avg_barons": rnd(stats.get("avg_barons")),
        "avg_heralds": rnd(stats.get("avg_heralds")),
        "gold_diff_10": rnd(stats.get("avg_golddiff10"), 0),
        "gold_diff_15": rnd(stats.get("avg_golddiff15"), 0),
    }

    return render_template("team.html", team=team_data)


@app.route("/api/teams")
def api_teams():
    """API: list teams, optionally filtered by region."""
    if not _load_predictor():
        return jsonify({"error": "No data loaded"}), 503
    region = request.args.get("region", "")
    if region and region in TOP_REGIONS:
        league_ids = TOP_REGIONS[region]
        filtered = [t for t in _all_teams if t["league"] in league_ids]
        return jsonify(filtered)
    return jsonify(_all_teams)


if __name__ == "__main__":
    _load_predictor()
    app.run(host="0.0.0.0", port=3080, debug=True)
