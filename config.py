"""
LoL Match Predictor - Configuration

Data source: Oracle's Elixir (https://oracleselixir.com)
Free professional LoL esports match data, updated daily.
"""

# Oracle's Elixir CSV download
# Primary: S3 bucket (current, updated daily)
# Fallback: Google Drive (older, may be stale)
# Source: https://oracleselixir.com/tools/downloads
#
# S3 URL pattern (date suffix changes daily):
#   https://oracleselixir-downloadable-match-data.s3-us-west-2.amazonaws.com/
#   {YEAR}_LoL_esports_match_data_from_OraclesElixir_{YYYYMMDD}.csv
#
# To update: visit https://oracleselixir.com/tools/downloads and copy links.

ORACLE_ELIXIR_S3_BUCKET = (
    "https://oracleselixir-downloadable-match-data.s3-us-west-2.amazonaws.com"
)

# Google Drive fallback URLs (may be outdated)
ORACLE_ELIXIR_URLS = {
    2026: "https://drive.google.com/uc?id=1v6LRphp2kYciU4SXp0PCjEMuev1bDejc",
    2025: "https://drive.google.com/uc?id=1v6LRphp2kYciU4SXp0PCjEMuev1bDejc",
    2024: "https://drive.google.com/uc?id=1IjIEhLc9n8eLKeY-yh_YigKVWbhgGBsN",
    2023: "https://drive.google.com/uc?id=1XXk2LO0CsNADBB1LRGOV5rUpyZdEZ8s2",
    2022: "https://drive.google.com/uc?id=1EHmptHyzY8owv0BAcNKtkQpMwfkURwRy",
}

# Top 5 regions — maps display name to ALL Oracle's Elixir league IDs
# that belong to that region (including cups, qualifiers, academy, etc.)
TOP_REGIONS = {
    "LCK": ["LCK", "LCK CL", "LCK Cup", "LCKC", "KeSPA"],
    "LPL": ["LPL"],
    "LEC": ["LEC"],
    "LCS": ["LCS", "LTA", "LTA N", "LTA S", "LTA North", "LTA South", "LTAN", "LTAS"],
    "PCS": ["PCS"],
}

# All league identifiers that map to top 5 regions
ALL_TOP_LEAGUE_IDS = []
for league_ids in TOP_REGIONS.values():
    ALL_TOP_LEAGUE_IDS.extend(league_ids)

# Reverse mapping: league_id -> canonical region name
LEAGUE_TO_REGION = {}
for region, league_ids in TOP_REGIONS.items():
    for lid in league_ids:
        LEAGUE_TO_REGION[lid] = region

# International tournaments — these games count for Elo but
# don't determine a team's "home league"
INTERNATIONAL_TOURNAMENTS = [
    "MSI", "Worlds", "WLDs",
    "All-Star", "Rift Rivals",
    "Asian Games",
]

# Elo rating parameters
ELO_INITIAL = 1500
ELO_K_FACTOR = 32
ELO_SEASON_DECAY = 0.75  # How much Elo regresses to mean between seasons

# Rolling average window for team stats (number of games)
ROLLING_WINDOW = 15

# Data directory
DATA_DIR = "data"
