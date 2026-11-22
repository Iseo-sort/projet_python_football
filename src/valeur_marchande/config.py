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
REFERENCE_DATE = "2026-09-10"   # date à laquelle on prend la valeur marchande
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
