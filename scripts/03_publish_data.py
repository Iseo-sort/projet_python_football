"""Dépose les données (data/raw et data/processed) sur le bucket du SSP Cloud.

À lancer après une collecte à la source, pour mettre à jour la copie figée que lisent
les scripts et les notebooks. Nécessite les droits d'écriture sur le bucket.
Usage : python scripts/03_publish_data.py
"""

from valeur_marchande import config, storage

fichiers = storage.publish()
print(f"{len(fichiers)} fichiers sur le bucket ({config.DATA_URL}) :")
for fichier in fichiers:
    print(" ", fichier)
