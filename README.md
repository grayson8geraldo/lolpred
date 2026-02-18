# LoL Match Predictor

Prediction system for professional League of Legends esports matches. Generates predictions for match winners, series scores (BO3/BO5), game duration, and first objectives (tower, dragon, blood, herald).

## Data Sources

**Primary: [Oracle's Elixir](https://oracleselixir.com)**
- Free CSV downloads with 100+ stats per game
- Updated daily, covers all major leagues from 2014 to present
- Includes: result, gamelength, firsttower, firstdragon, firstblood, firstherald, firstbaron, gold differentials at 10/15 min, kills/deaths/assists, objective counts, and more
- Download page: https://oracleselixir.com/tools/downloads

**Supplementary:**
- [gol.gg](https://gol.gg) — Tournament/team/player stats with detailed objective rates
- [Leaguepedia](https://lol.fandom.com) — Community wiki with match data and API
- [LoL Esports Data Portal](https://grid.gg/get-league-of-legends/) — Official Riot data via GRID/Bayes

## Covered Regions (Top 5)

| Region | League IDs | Description |
|--------|-----------|-------------|
| LCK | LCK | Korea |
| LPL | LPL | China |
| LEC | LEC | Europe |
| LCS | LCS, LTA, LTA North | North America |
| PCS | PCS | Pacific |

## Predictions

1. **Match Winner** — Win probability based on Elo ratings adjusted by recent form, early game economy, and KDA
2. **Map Count (BO3/BO5)** — Score line distribution (e.g., 2-0, 2-1, 3-0, 3-1, 3-2) using binomial model from per-game win probability
3. **Game Duration** — Predicted minutes + over/under probabilities for standard lines (25.5, 28.5, 30.5, 32.5 min)
4. **First Tower** — Which team takes first tower, based on comparative first tower rates
5. **First Dragon** — Which team takes first dragon
6. **First Blood** — Which team gets first kill
7. **First Herald** — Which team takes first Rift Herald

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Download real data (Oracle's Elixir)
```bash
python main.py download                    # Downloads 2024-2025 data
python main.py download --years 2023 2024 2025
python main.py download --force            # Re-download existing files
```

### Generate sample data (for testing)
```bash
python main.py generate                    # Generates simulated 2024-2025 data
```

### Predict a match
```bash
python main.py predict "T1" "Gen.G" --format BO3
python main.py predict "Bilibili Gaming" "Top Esports" --format BO5
python main.py predict "G2 Esports" "Fnatic" --format BO1
```

### View rankings
```bash
python main.py rankings                    # Global top 30
python main.py rankings --region LCK       # LCK only
python main.py rankings --region LPL
```

### List teams
```bash
python main.py teams                       # All teams from top 5 regions
python main.py teams --region LEC
```

### Team statistics
```bash
python main.py stats "T1"
python main.py stats "Gen.G"
```

## Prediction Strategy

### Elo Rating System
- Initial rating: 1500
- K-factor: 32
- Season decay: ratings regress 25% toward mean between years
- Updated after every game (not series)

### Win Probability Adjustment
Base Elo probability is adjusted by:
- **Recent form** (last 15 games win rate differential) — weight: 15%
- **Early game gold differential** (avg gold diff at 10 min) — weight: up to 10%
- **Kill/Death ratio** comparison — weight: 5%

### Map Count Model
Uses binomial distribution with the adjusted per-game win probability:
- BO3: P(2-0) = p², P(2-1) = 2pq·p, P(0-2) = q², P(1-2) = 2pq·q
- BO5: Negative binomial for first to 3 wins

### Duration Model
- Predicted duration = average of both teams' mean game lengths
- Over/under probabilities use logistic approximation with std dev of ~4.5 minutes

### First Objectives
- Compares each team's historical rate for the objective
- Normalized to produce head-to-head probability

## Data Fields Used

From Oracle's Elixir CSV (team-level rows):

| Field | Type | Description |
|-------|------|-------------|
| result | 0/1 | Win/loss |
| gamelength | int | Game duration in seconds |
| firsttower | 0/1 | Got first tower |
| firstdragon | 0/1 | Got first dragon |
| firstblood | 0/1 | Got first blood |
| firstherald | 0/1 | Got first herald |
| firstbaron | 0/1 | Got first baron |
| golddiffat10 | int | Gold differential at 10 min |
| golddiffat15 | int | Gold differential at 15 min |
| kills/deaths/assists | int | Combat stats |
| dragons/towers/barons | int | Objective counts |

## Project Structure

```
lolpred/
├── main.py              # CLI entry point
├── config.py            # Configuration (URLs, regions, parameters)
├── requirements.txt     # Python dependencies
├── data/                # Downloaded CSV data (gitignored)
└── src/
    ├── data_loader.py   # Download and parse Oracle's Elixir data
    ├── features.py      # Elo system + rolling team statistics
    ├── predictor.py     # Prediction engine
    ├── display.py       # Terminal output formatting
    └── sample_data.py   # Sample data generator for testing
```
