"""Télécharge les données Transfermarkt et construit les tableaux d'analyse.

Usage : python scripts/01_collect_transfermarkt.py
"""

from valeur_marchande import transfermarkt

transfermarkt.download_tables()
tables = transfermarkt.load_tables()
snapshot = transfermarkt.build_snapshot(tables)
transfermarkt.save_snapshot(snapshot)

print(f"{len(snapshot)} joueurs enregistrés dans data/processed/players_snapshot.parquet")

panel = transfermarkt.build_panel(tables)
transfermarkt.save_panel(panel)
print(f"{len(panel)} lignes joueur x saison enregistrées dans data/processed/players_panel.parquet")
