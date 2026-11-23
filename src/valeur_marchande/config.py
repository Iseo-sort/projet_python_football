"""Paramètres du projet, regroupés au même endroit."""

import os
from pathlib import Path

# Dossiers (la racine du projet est deux niveaux au-dessus de ce fichier)
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# Source : tables Transfermarkt publiées par le projet dcaribou/transfermarkt-datasets
BASE_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"

# Paramètres de l'étude (à discuter en groupe)
REFERENCE_DATE = "2026-06-30"   # date à laquelle on prend la valeur marchande
# Saisons dont on agrège les performances : de 2022-23 à 2025-26
SEASONS = {
    f"{a}_{str(a + 1)[2:]}": (f"{a}-07-01", f"{a + 1}-06-30")
    for a in range(2022, 2026)
}

LEAGUES = ["GB1", "ES1", "IT1", "L1", "FR1", "NL1", "PO1", "BE1", "TR1"]
MAX_VALUATION_AGE_DAYS = 365    # on écarte les valeurs plus vieilles qu'un an

# Fichier final (snapshot) et son URL publique sur le bucket
SNAPSHOT_PATH = PROCESSED_DIR / "players_snapshot.parquet"
SNAPSHOT_URL = os.environ.get("SNAPSHOT_URL", "")

# Tableau « joueur x saison » (variations de valeur) et son URL publique
PANEL_PATH = PROCESSED_DIR / "players_panel.parquet"
PANEL_URL = os.environ.get("PANEL_URL", "")

# Notes EA SPORTS FC : site officiel (édition en cours) et API (édition précédente)
EA_RATINGS_URL = "https://www.ea.com/games/ea-sports-fc/ratings"
EA_API_URL = "https://drop-api.ea.com/rating/ea-sports-fc"

# Éditions récupérées sur Kaggle : (base, fichier, valeur de la colonne fifa_version)
KAGGLE_DATASETS = {
    "fifa23": ("stefanoleone992/ea-sports-fc-24-complete-player-dataset", "male_players.csv", 23),
    "fc24": ("stefanoleone992/ea-sports-fc-24-complete-player-dataset", "male_players.csv", 24),
    "fc25": ("nyagami/ea-sports-fc-25-database-ratings-and-stats", "male_players.csv", None),
}

# Édition EA sortie en septembre de chaque année (= note au début de la saison qui commence)
EA_EDITIONS = {2022: "fifa23", 2023: "fc24", 2024: "fc25", 2025: "fc26", 2026: "fc27"}

# Notes EA associées aux joueurs Transfermarkt (une ligne par joueur et par édition)
EA_MATCHED_PATH = PROCESSED_DIR / "ea_ratings_matched.parquet"
EA_MATCHED_URL = os.environ.get("EA_MATCHED_URL", "")
