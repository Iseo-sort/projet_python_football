"""Télécharge les données Transfermarkt et construit le tableau final.

Usage : python scripts/01_collect_transfermarkt.py
"""

from valeur_marchande import transfermarkt

transfermarkt.download_tables()
tables = transfermarkt.load_tables()
snapshot = transfermarkt.build_snapshot(tables)
transfermarkt.save_snapshot(snapshot)

print(f"{len(snapshot)} joueurs enregistrés dans data/processed/players_snapshot.parquet")
print(snapshot.head())
