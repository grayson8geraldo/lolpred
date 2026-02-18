"""
Sample Data Generator - Creates realistic test data matching Oracle's Elixir format.

Used for testing and demonstration when actual data downloads are unavailable.
Based on real statistical distributions from professional LoL matches.

The generated data simulates matches from the top 5 regions:
LCK, LPL, LEC, LCS, PCS for 2024-2025 seasons.
"""

import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Real team names from top 5 regions (2024-2025 rosters)
TEAMS = {
    "LCK": [
        "T1", "Gen.G", "Hanwha Life Esports", "Dplus KIA",
        "KT Rolster", "Kwangdong Freecs", "DRX", "Nongshim RedForce",
        "BNK FearX", "OK BRION",
    ],
    "LPL": [
        "Bilibili Gaming", "Top Esports", "JD Gaming", "LNG Esports",
        "Weibo Gaming", "FunPlus Phoenix", "Royal Never Give Up", "ThunderTalk Gaming",
        "Anyone's Legend", "Team WE",
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
        "PSG Talon", "CTBC Flying Oyster", "Frank Esports", "Deep Cross Gaming",
        "Beyond Gaming", "Impunity", "J Team", "Hong Kong Attitude",
    ],
}

# Approximate team strength tiers (affects simulated stats)
TEAM_STRENGTH = {
    # LCK
    "T1": 0.85, "Gen.G": 0.88, "Hanwha Life Esports": 0.80,
    "Dplus KIA": 0.72, "KT Rolster": 0.68, "Kwangdong Freecs": 0.60,
    "DRX": 0.58, "Nongshim RedForce": 0.50, "BNK FearX": 0.55,
    "OK BRION": 0.45,
    # LPL
    "Bilibili Gaming": 0.82, "Top Esports": 0.78, "JD Gaming": 0.80,
    "LNG Esports": 0.75, "Weibo Gaming": 0.72, "FunPlus Phoenix": 0.65,
    "Royal Never Give Up": 0.60, "ThunderTalk Gaming": 0.48,
    "Anyone's Legend": 0.45, "Team WE": 0.50,
    # LEC
    "G2 Esports": 0.75, "Fnatic": 0.72, "MAD Lions KOI": 0.65,
    "Team Vitality": 0.60, "SK Gaming": 0.55, "Rogue": 0.58,
    "Team BDS": 0.52, "Team Heretics": 0.50, "Karmine Corp": 0.62,
    "GIANTX": 0.48,
    # LCS
    "Cloud9": 0.68, "Team Liquid": 0.70, "FlyQuest": 0.72,
    "100 Thieves": 0.62, "NRG": 0.55, "Dignitas": 0.52,
    "Immortals": 0.45, "Golden Guardians": 0.48,
    # PCS
    "PSG Talon": 0.65, "CTBC Flying Oyster": 0.58,
    "Frank Esports": 0.52, "Deep Cross Gaming": 0.48,
    "Beyond Gaming": 0.55, "Impunity": 0.42, "J Team": 0.50,
    "Hong Kong Attitude": 0.45,
}


def generate_sample_data(years: list[int] = None) -> pd.DataFrame:
    """Generate realistic match data matching Oracle's Elixir CSV format."""
    if years is None:
        years = [2024, 2025]

    all_rows = []
    game_id_counter = 50000

    for year in years:
        for league, teams in TEAMS.items():
            # Each team plays roughly 18 BO3 matches per split (2 splits)
            for split in ["Spring", "Summer"]:
                # Set date range
                if split == "Spring":
                    start_date = datetime(year, 1, 15)
                    end_date = datetime(year, 4, 15)
                else:
                    start_date = datetime(year, 6, 1)
                    end_date = datetime(year, 8, 30)

                if year == 2025 and split == "Summer":
                    end_date = min(end_date, datetime(2025, 12, 31))

                # Generate round-robin matches
                for i in range(len(teams)):
                    for j in range(i + 1, len(teams)):
                        team_a = teams[i]
                        team_b = teams[j]

                        # Determine number of games (BO3)
                        str_a = TEAM_STRENGTH.get(team_a, 0.5)
                        str_b = TEAM_STRENGTH.get(team_b, 0.5)

                        # Add noise to strength
                        eff_a = str_a + random.gauss(0, 0.1)
                        eff_b = str_b + random.gauss(0, 0.1)

                        # Win probability for team_a in a single game
                        p_a = eff_a / (eff_a + eff_b)

                        # Simulate BO3
                        wins_a = 0
                        wins_b = 0
                        game_num = 0
                        match_date = start_date + timedelta(
                            days=random.randint(0, (end_date - start_date).days)
                        )

                        while wins_a < 2 and wins_b < 2:
                            game_num += 1
                            game_id_counter += 1
                            gameid = f"OE:{year}:{game_id_counter}"

                            # Simulate game result
                            a_wins = random.random() < p_a
                            if a_wins:
                                wins_a += 1
                            else:
                                wins_b += 1

                            # Generate game stats
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
                                str_a=eff_a,
                                str_b=eff_b,
                            )
                            all_rows.extend(game_rows)

    df = pd.DataFrame(all_rows)
    return df


def _generate_game_rows(gameid, team_a, team_b, a_wins, league, year,
                        split, date, game_num, str_a, str_b):
    """Generate the 2 team rows for a single game."""
    # Game duration: stronger team advantage = shorter games on average
    winner_str = str_a if a_wins else str_b
    base_duration = 1800 + random.gauss(0, 180)  # ~30 min base
    # Stronger teams tend to close games faster
    duration_adj = (1 - winner_str) * 300
    gamelength = max(900, int(base_duration + duration_adj))

    # Who gets first objectives (influenced by team strength)
    # Winner tends to get first objectives more often
    winner_bonus = 0.15

    def first_obj(str_winner, str_loser, base_advantage=0):
        """Return (winner_gets_it, loser_gets_it) as 1/0."""
        p = (str_winner + winner_bonus + base_advantage) / (
            str_winner + str_loser + winner_bonus + base_advantage
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

    # Kill stats
    minutes = gamelength / 60
    if a_wins:
        kills_a = max(1, int(random.gauss(15, 5) * str_a))
        kills_b = max(0, int(random.gauss(10, 4) * str_b))
    else:
        kills_b = max(1, int(random.gauss(15, 5) * str_b))
        kills_a = max(0, int(random.gauss(10, 4) * str_a))

    deaths_a = kills_b
    deaths_b = kills_a

    # Objectives for winner
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

    # Gold stats
    base_gold = int(minutes * 1800)
    if a_wins:
        gold_a = base_gold + random.randint(1000, 5000)
        gold_b = base_gold - random.randint(0, 3000)
    else:
        gold_b = base_gold + random.randint(1000, 5000)
        gold_a = base_gold - random.randint(0, 3000)

    # Early game gold diff (@10, @15 min)
    advantage = str_a - str_b
    gd10 = int(advantage * 2000 + random.gauss(0, 800))
    gd15 = int(advantage * 3000 + random.gauss(0, 1200))
    xpd10 = int(advantage * 1500 + random.gauss(0, 600))
    xpd15 = int(advantage * 2500 + random.gauss(0, 1000))

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
