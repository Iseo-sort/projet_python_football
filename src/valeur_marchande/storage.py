"""Copie figée des données sur le stockage du SSP Cloud (bucket S3).

Les sources (Transfermarkt, sites d'EA, Kaggle) changent avec le temps. Pour que le projet
donne toujours les mêmes résultats, les fichiers bruts (data/raw) et les tableaux finaux
(data/processed) sont déposés une fois pour toutes sur le bucket, dans un dossier public :
les scripts et les notebooks les y lisent quand ils ne sont pas présents en local.
"""

import requests
import pandas as pd

from valeur_marchande import config

DATA_DIR = config.ROOT / "data"


def bucket_url(chemin):
    """Adresse publique sur le bucket d'un fichier de data/, ex. data/raw/clubs.csv.gz."""
    return f"{config.DATA_URL}/{chemin.relative_to(DATA_DIR).as_posix()}"


def download_from_bucket(chemin):
    """Télécharge depuis le bucket un fichier de data/ absent en local."""
    print(f"Téléchargement de {chemin.name} depuis le bucket...")
    reponse = requests.get(bucket_url(chemin), timeout=600)
    reponse.raise_for_status()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(reponse.content)


def read_parquet(chemin):
    """Lit un tableau final : fichier local s'il existe, sinon copie du bucket."""
    if chemin.exists():
        return pd.read_parquet(chemin)
    return pd.read_parquet(bucket_url(chemin))


def publish():
    """Dépose data/raw et data/processed sur le bucket (remplace les fichiers existants).

    Nécessite les identifiants du SSP Cloud (variables AWS_* présentes dans les services
    du datalab) et les droits d'écriture sur le bucket config.BUCKET_PATH.
    """
    import s3fs  # importé ici : inutile pour seulement lire les données

    fs = s3fs.S3FileSystem(client_kwargs={"endpoint_url": config.S3_ENDPOINT})
    for dossier in ("raw", "processed"):
        fs.put(f"{DATA_DIR / dossier}/", f"{config.BUCKET_PATH}/{dossier}/", recursive=True)
    return fs.find(config.BUCKET_PATH)
