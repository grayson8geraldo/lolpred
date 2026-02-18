"""
LoL Match Predictor - Configuration

Data source: Oracle's Elixir (https://oracleselixir.com)
Free professional LoL esports match data, updated daily.
"""

# Oracle's Elixir CSV download URLs (Google Drive)
# Source: https://oracleselixir.com/tools/downloads
ORACLE_ELIXIR_URLS = {
    2026: "https://drive.google.com/uc?id=1v6LRphp2kYciU4SXp0PCjEMuev1bDejc",
    2025: "https://drive.google.com/uc?id=1v6LRphp2kYciU4SXp0PCjEMuev1bDejc",
    2024: "https://drive.google.com/uc?id=1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN",
    2023: "https://drive.google.com/uc?id=1XXk2LO0CsNADBB1LRGOV5rUpyZdEZ8s2",
    2022: "https://drive.google.com/uc?id=1EHmptHyzY8owv0BAcNKtkQpMwfkURwRy",
}

# Top 5 regions to track
# LCK (Korea), LPL (China), LEC (Europe), LCS/LTA (North America), PCS (Pacific)
TOP_REGIONS = {
    "LCK": ["LCK"],
    "LPL": ["LPL"],
    "LEC": ["LEC"],
    "LCS": ["LCS", "LTA", "LTA North"],
    "PCS": ["PCS"],
}

# All league identifiers that map to top 5 regions
ALL_TOP_LEAGUE_IDS = []
for league_ids in TOP_REGIONS.values():
    ALL_TOP_LEAGUE_IDS.extend(league_ids)

# International tournaments to include
INTERNATIONAL_TOURNAMENTS = ["MSI", "Worlds", "WLDs"]

# Elo rating parameters
ELO_INITIAL = 1500
ELO_K_FACTOR = 32
ELO_SEASON_DECAY = 0.75  # How much Elo regresses to mean between seasons

# Rolling average window for team stats (number of games)
ROLLING_WINDOW = 15

# Data directory
DATA_DIR = "data"
