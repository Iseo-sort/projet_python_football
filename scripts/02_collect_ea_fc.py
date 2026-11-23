"""Télécharge les notes EA SPORTS FC et les associe aux joueurs Transfermarkt.

À lancer après scripts/01_collect_transfermarkt.py (il utilise le panel).
Usage : python scripts/02_collect_ea_fc.py            (données brutes figées, lues sur le bucket)
        python scripts/02_collect_ea_fc.py --source   (données brutes collectées à la source)
"""

import sys

from valeur_marchande import ea_fc, transfermarkt

# Par défaut, les données brutes viennent de la copie figée du bucket (reproductible)
FROM_SOURCE = "--source" in sys.argv

# Éditions collectées : FIFA 23 à FC 25 sur Kaggle (compte nécessaire, voir README),
# FC 26 et FC 27 sur les sites d'EA
EDITIONS = ["fifa23", "fc24", "fc25", "fc26", "fc27"]

for edition in EDITIONS:
    ea_fc.download_ratings(edition, from_source=FROM_SOURCE)

# Joueurs à apparier : tous ceux du panel (ils incluent ceux du snapshot)
panel = transfermarkt.load_panel()
joueurs = panel.drop_duplicates("player_id")

apparies = ea_fc.build_matched(joueurs, EDITIONS)
ea_fc.save_matched(apparies)

snapshot = transfermarkt.load_snapshot()
for edition in EDITIONS:
    groupe = apparies[apparies["edition"] == edition]
    part = snapshot["player_id"].isin(groupe["player_id"]).mean()
    print(f"{edition} : {len(groupe)} joueurs appariés, dont {part:.1%} des joueurs du snapshot")
