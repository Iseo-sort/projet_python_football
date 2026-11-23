"""Télécharge les données Transfermarkt et construit les tableaux d'analyse.

Usage : python scripts/01_collect_transfermarkt.py            (données brutes figées, lues sur le bucket)
        python scripts/01_collect_transfermarkt.py --source   (données brutes collectées à la source)
"""

import sys

from valeur_marchande import transfermarkt

# Par défaut, les données brutes viennent de la copie figée du bucket (reproductible)
FROM_SOURCE = "--source" in sys.argv

transfermarkt.download_tables(from_source=FROM_SOURCE)
tables = transfermarkt.load_tables()
snapshot = transfermarkt.build_snapshot(tables)
transfermarkt.save_snapshot(snapshot)

print(f"{len(snapshot)} joueurs enregistrés dans data/processed/players_snapshot.parquet")

panel = transfermarkt.build_panel(tables)
transfermarkt.save_panel(panel)
print(f"{len(panel)} lignes joueur x saison enregistrées dans data/processed/players_panel.parquet")
