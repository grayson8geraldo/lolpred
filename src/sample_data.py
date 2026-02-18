"""
Sample Data Generator - Creates realistic test data matching Oracle's Elixir format.

Used for testing and demonstration when actual data downloads are unavailable.
Based on real statistical distributions from professional LoL matches.

The generated data simulates matches from the top 5 regions:
LCK, LPL, LEC, LCS/LTA, PCS for 2024-2026 seasons.
"""

import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Real team names from top 5 regions by year
TEAMS_BY_YEAR = {
    2024: {
        "LCK": [
            "T1", "Gen.G", "Hanwha Life Esports", "Dplus KIA",
            "KT Rolster", "Kwangdong Freecs", "DRX", "Nongshim RedForce",
            "BNK FearX", "OK BRION",
        ],
        "LPL": [
            "Bilibili Gaming", "Top Esports", "JD Gaming", "LNG Esports",
            "Weibo Gaming", "FunPlus Phoenix", "Royal Never Give Up",
            "ThunderTalk Gaming", "Anyone's Legend", "Team WE",
        ],
        "LEC": [
            "G2 Esports", "Fnatic", "MAD Lions KOI", "Team Vitality",
            "SK Gaming", "Rogue", "Team BDS", "Team Heretics",
            "Karmine Corp", "GIANTX",
        ],
        "LCS": [
            "Cloud9", "Team Liquid", "FlyQuest", "100 Thieves",
            "NRG", "Dignitas", "Immortals", "Golden Guardians",
        ],
        "PCS": [
            "PSG Talon", "CTBC Flying Oyster", "Frank Esports",
            "Deep Cross Gaming", "Beyond Gaming", "Impunity",
            "J Team", "Hong Kong Attitude",
        ],
    },
    2025: {
        "LCK": [
            "T1", "Gen.G", "Hanwha Life Esports", "Dplus KIA",
            "KT Rolster", "Kwangdong Freecs", "DRX", "Nongshim RedForce",
            "BNK FearX", "OK BRION",
        ],
        "LPL": [
            "Bilibili Gaming", "Top Esports", "JD Gaming", "LNG Esports",
            "Weibo Gaming", "FunPlus Phoenix", "Royal Never Give Up",
            "ThunderTalk Gaming", "Anyone's Legend", "Ninjas in Pyjamas",
        ],
        "LEC": [
            "G2 Esports", "Fnatic", "MAD Lions KOI", "Team Vitality",
            "SK Gaming", "Rogue", "Team BDS", "Team Heretics",
            "Karmine Corp", "GIANTX",
        ],
        "LCS": [
            "Cloud9", "Team Liquid", "FlyQuest", "100 Thieves",
            "Shopify Rebellion", "Dignitas", "Immortals", "Lyon Gaming",
        ],
        "PCS": [
            "PSG Talon", "CTBC Flying Oyster", "Frank Esports",
            "Deep Cross Gaming", "Beyond Gaming", "Impunity",
            "J Team", "Hong Kong Attitude",
        ],
    },
    2026: {
        "LCK": [
            "T1", "Gen.G", "Hanwha Life Esports", "Dplus KIA",
            "KT Rolster", "Kwangdong Freecs", "DRX", "Nongshim RedForce",
            "BNK FearX", "OK BRION",
        ],
        "LPL": [
            "Bilibili Gaming", "Top Esports", "JD Gaming", "LNG Esports",
            "Weibo Gaming", "FunPlus Phoenix", "Royal Never Give Up",
            "ThunderTalk Gaming", "Anyone's Legend", "Ninjas in Pyjamas",
        ],
        "LEC": [
            "G2 Esports", "Fnatic", "MAD Lions KOI", "Team Vitality",
            "SK Gaming", "Rogue", "Team BDS", "Team Heretics",
            "Karmine Corp", "GIANTX",
        ],
        "LCS": [
            "Cloud9", "Team Liquid", "FlyQuest", "100 Thieves",
            "Shopify Rebellion", "Dignitas", "Immortals", "Lyon Gaming",
        ],
        "PCS": [
            "PSG Talon", "CTBC Flying Oyster", "Frank Esports",
            "Deep Cross Gaming", "Beyond Gaming", "Impunity",
            "J Team", "Hong Kong Attitude",
        ],
    },
}

# Backward compat: flat team list (union of all years)
TEAMS = {}
for _year_teams in TEAMS_BY_YEAR.values():
    for _league, _tlist in _year_teams.items():
        if _league not in TEAMS:
            TEAMS[_league] = []
        for _t in _tlist:
            if _t not in TEAMS[_league]:
                TEAMS[_league].append(_t)

# Team strength tiers — this heavily controls Elo differentiation.
# Range 0.0-1.0; top teams ~0.85-0.92, bottom ~0.30-0.45.
TEAM_STRENGTH = {
    # LCK — strongest region overall
    "Gen.G": 0.92, "T1": 0.90, "Hanwha Life Esports": 0.84,
    "Dplus KIA": 0.74, "KT Rolster": 0.70, "DRX": 0.65,
    "Kwangdong Freecs": 0.58, "BNK FearX": 0.54,
    "Nongshim RedForce": 0.48, "OK BRION": 0.40,
    # LPL
    "Bilibili Gaming": 0.88, "JD Gaming": 0.85, "Top Esports": 0.82,
    "LNG Esports": 0.78, "Weibo Gaming": 0.73, "FunPlus Phoenix": 0.68,
    "Royal Never Give Up": 0.62, "ThunderTalk Gaming": 0.46,
    "Anyone's Legend": 0.42, "Team WE": 0.44, "Ninjas in Pyjamas": 0.50,
    # LEC
    "G2 Esports": 0.80, "Fnatic": 0.76, "MAD Lions KOI": 0.68,
    "Karmine Corp": 0.64, "Team Vitality": 0.60, "Team BDS": 0.55,
    "Team Heretics": 0.52, "SK Gaming": 0.50, "Rogue": 0.48,
    "GIANTX": 0.42,
    # LCS / LTA
    "FlyQuest": 0.72, "Team Liquid": 0.70, "Cloud9": 0.68,
    "100 Thieves": 0.62, "Shopify Rebellion": 0.55, "Dignitas": 0.50,
    "NRG": 0.48, "Immortals": 0.40, "Golden Guardians": 0.42,
    "Lyon Gaming": 0.44,
    # PCS
    "PSG Talon": 0.70, "CTBC Flying Oyster": 0.60,
    "Beyond Gaming": 0.55, "Frank Esports": 0.52,
    "Deep Cross Gaming": 0.48, "J Team": 0.46,
    "Impunity": 0.38, "Hong Kong Attitude": 0.40,
}


def _win_probability(str_a: float, str_b: float) -> float:
    """Calculate single-game win probability for team A using logistic model."""
    # Logistic-style: stronger differentiation than simple ratio
    diff = str_a - str_b
    return 1.0 / (1.0 + 10 ** (-diff * 4))


def generate_sample_data(years: list[int] = None) -> pd.DataFrame:
    """Generate realistic match data matching Oracle's Elixir CSV format."""
    if years is None:
        years = [2024, 2025, 2026]

    all_rows = []
    game_id_counter = 50000

    for year in years:
        year_teams = TEAMS_BY_YEAR.get(year, TEAMS_BY_YEAR.get(2026, {}))

        for league, teams in year_teams.items():
            for split in ["Spring", "Summer"]:
                if split == "Spring":
                    start_date = datetime(year, 1, 15)
                    end_date = datetime(year, 4, 15)
                else:
                    start_date = datetime(year, 6, 1)
                    end_date = datetime(year, 8, 30)

                # For current year, cap at today
                today = datetime.now()
                if end_date > today:
                    end_date = today - timedelta(days=1)
                if start_date > today:
                    continue  # skip future splits

                # Generate round-robin matches
                for i in range(len(teams)):
                    for j in range(i + 1, len(teams)):
                        team_a = teams[i]
                        team_b = teams[j]

                        str_a = TEAM_STRENGTH.get(team_a, 0.5)
                        str_b = TEAM_STRENGTH.get(team_b, 0.5)

                        # Win probability uses logistic model for strong differentiation
                        p_a = _win_probability(str_a, str_b)

                        # Simulate BO3
                        wins_a = 0
                        wins_b = 0
                        game_num = 0
                        days_range = max(1, (end_date - start_date).days)
                        match_date = start_date + timedelta(
                            days=random.randint(0, days_range)
                        )

                        while wins_a < 2 and wins_b < 2:
                            game_num += 1
                            game_id_counter += 1
                            gameid = f"OE:{year}:{game_id_counter}"

                            # Add per-game noise but keep general direction
                            noise = random.gauss(0, 0.08)
                            game_p = max(0.05, min(0.95, p_a + noise))
                            a_wins = random.random() < game_p

                            if a_wins:
                                wins_a += 1
                            else:
                                wins_b += 1

                            game_rows = _generate_game_rows(
                                gameid=gameid,
                                team_a=team_a,
                                team_b=team_b,
                                a_wins=a_wins,
                                league=league,
                                year=year,
                                split=split,
                                date=match_date,
                                game_num=game_num,
                                str_a=str_a,
                                str_b=str_b,
                            )
                            all_rows.extend(game_rows)

    df = pd.DataFrame(all_rows)
    return df


def _generate_game_rows(gameid, team_a, team_b, a_wins, league, year,
                        split, date, game_num, str_a, str_b):
    """Generate the 2 team rows for a single game."""
    winner_str = str_a if a_wins else str_b
    loser_str = str_b if a_wins else str_a

    # Duration: strong winners close games faster
    base_duration = 1800 + random.gauss(0, 150)
    strength_gap = abs(winner_str - loser_str)
    duration_adj = -strength_gap * 400 + (1 - winner_str) * 200
    gamelength = max(1000, int(base_duration + duration_adj))

    winner_bonus = 0.18

    def first_obj(str_w, str_l, base_advantage=0):
        p = (str_w + winner_bonus + base_advantage) / (
            str_w + str_l + winner_bonus + base_advantage
        )
        winner_first = random.random() < p
        return (1 if winner_first else 0, 0 if winner_first else 1)

    if a_wins:
        fb_a, fb_b = first_obj(str_a, str_b)
        ft_a, ft_b = first_obj(str_a, str_b)
        fd_a, fd_b = first_obj(str_a, str_b)
        fh_a, fh_b = first_obj(str_a, str_b)
        fba_a, fba_b = first_obj(str_a, str_b, 0.1)
        fmt_a, fmt_b = first_obj(str_a, str_b)
        f3t_a, f3t_b = first_obj(str_a, str_b, 0.05)
    else:
        fb_b, fb_a = first_obj(str_b, str_a)
        ft_b, ft_a = first_obj(str_b, str_a)
        fd_b, fd_a = first_obj(str_b, str_a)
        fh_b, fh_a = first_obj(str_b, str_a)
        fba_b, fba_a = first_obj(str_b, str_a, 0.1)
        fmt_b, fmt_a = first_obj(str_b, str_a)
        f3t_b, f3t_a = first_obj(str_b, str_a, 0.05)

    # Kill stats — reflect team strength
    minutes = gamelength / 60
    if a_wins:
        kills_a = max(1, int(random.gauss(14, 4) * (0.7 + str_a * 0.5)))
        kills_b = max(0, int(random.gauss(8, 3) * (0.7 + str_b * 0.4)))
    else:
        kills_b = max(1, int(random.gauss(14, 4) * (0.7 + str_b * 0.5)))
        kills_a = max(0, int(random.gauss(8, 3) * (0.7 + str_a * 0.4)))

    deaths_a = kills_b
    deaths_b = kills_a

    if a_wins:
        dragons_a = random.randint(3, 5)
        dragons_b = random.randint(0, 3)
        towers_a = random.randint(7, 11)
        towers_b = random.randint(1, 6)
        barons_a = random.randint(1, 3)
        barons_b = random.randint(0, 1)
    else:
        dragons_b = random.randint(3, 5)
        dragons_a = random.randint(0, 3)
        towers_b = random.randint(7, 11)
        towers_a = random.randint(1, 6)
        barons_b = random.randint(1, 3)
        barons_a = random.randint(0, 1)

    heralds_a = random.randint(0, 2)
    heralds_b = 2 - heralds_a

    # Gold — stronger teams earn more gold
    base_gold = int(minutes * 1800)
    if a_wins:
        gold_a = base_gold + random.randint(1500, 6000)
        gold_b = base_gold - random.randint(500, 4000)
    else:
        gold_b = base_gold + random.randint(1500, 6000)
        gold_a = base_gold - random.randint(500, 4000)

    # Early gold diff — reflects team strength difference strongly
    advantage = str_a - str_b
    gd10 = int(advantage * 3000 + random.gauss(0, 600))
    gd15 = int(advantage * 4500 + random.gauss(0, 900))
    xpd10 = int(advantage * 2000 + random.gauss(0, 500))
    xpd15 = int(advantage * 3500 + random.gauss(0, 800))

    side_a = random.choice(["Blue", "Red"])
    side_b = "Red" if side_a == "Blue" else "Blue"

    row_a = {
        "gameid": gameid, "league": league, "year": year, "split": split,
        "playoffs": 0, "date": date.strftime("%Y-%m-%d"),
        "game": game_num, "patch": f"{year % 100}.{random.randint(1, 24)}",
        "side": side_a, "position": "team", "teamname": team_a,
        "result": 1 if a_wins else 0,
        "gamelength": gamelength,
        "firstblood": fb_a, "firstdragon": fd_a, "firstherald": fh_a,
        "firstbaron": fba_a, "firsttower": ft_a,
        "firstmidtower": fmt_a, "firsttothreetowers": f3t_a,
        "kills": kills_a, "deaths": deaths_a,
        "assists": int(kills_a * random.uniform(1.8, 2.5)),
        "dragons": dragons_a, "opp_dragons": dragons_b,
        "towers": towers_a, "opp_towers": towers_b,
        "barons": barons_a, "opp_barons": barons_b,
        "heralds": heralds_a, "opp_heralds": heralds_b,
        "inhibitors": max(0, towers_a - 8), "opp_inhibitors": max(0, towers_b - 8),
        "totalgold": gold_a, "earnedgold": int(gold_a * 0.75),
        "golddiffat10": gd10, "xpdiffat10": xpd10,
        "csdiffat10": int(gd10 / 30),
        "golddiffat15": gd15, "xpdiffat15": xpd15,
        "csdiffat15": int(gd15 / 25),
        "goldat10": 15000 + gd10 // 2,
        "goldat15": 24000 + gd15 // 2,
        "ban1": "Champion_A", "ban2": "Champion_B", "ban3": "Champion_C",
        "ban4": "Champion_D", "ban5": "Champion_E",
    }

    row_b = {
        "gameid": gameid, "league": league, "year": year, "split": split,
        "playoffs": 0, "date": date.strftime("%Y-%m-%d"),
        "game": game_num, "patch": row_a["patch"],
        "side": side_b, "position": "team", "teamname": team_b,
        "result": 0 if a_wins else 1,
        "gamelength": gamelength,
        "firstblood": fb_b, "firstdragon": fd_b, "firstherald": fh_b,
        "firstbaron": fba_b, "firsttower": ft_b,
        "firstmidtower": fmt_b, "firsttothreetowers": f3t_b,
        "kills": kills_b, "deaths": deaths_b,
        "assists": int(kills_b * random.uniform(1.8, 2.5)),
        "dragons": dragons_b, "opp_dragons": dragons_a,
        "towers": towers_b, "opp_towers": towers_a,
        "barons": barons_b, "opp_barons": barons_a,
        "heralds": heralds_b, "opp_heralds": heralds_a,
        "inhibitors": max(0, towers_b - 8), "opp_inhibitors": max(0, towers_a - 8),
        "totalgold": gold_b, "earnedgold": int(gold_b * 0.75),
        "golddiffat10": -gd10, "xpdiffat10": -xpd10,
        "csdiffat10": -int(gd10 / 30),
        "golddiffat15": -gd15, "xpdiffat15": -xpd15,
        "csdiffat15": -int(gd15 / 25),
        "goldat10": 15000 - gd10 // 2,
        "goldat15": 24000 - gd15 // 2,
        "ban1": "Champion_F", "ban2": "Champion_G", "ban3": "Champion_H",
        "ban4": "Champion_I", "ban5": "Champion_J",
    }

    return [row_a, row_b]
