"""Collecte des données Transfermarkt et construction du tableau « une ligne par joueur »."""

from urllib.request import Request, urlopen
import pandas as pd

from valeur_marchande import config

# Les tables dont on a besoin
TABLES = ["players", "competitions", "player_valuations", "clubs", "appearances"]


def download_tables():
    """Télécharge les tables (fichiers .csv.gz) dans data/raw/, si elles n'y sont pas déjà."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for nom in TABLES:
        chemin = config.RAW_DIR / f"{nom}.csv.gz"
        if not chemin.exists():
            print(f"Téléchargement de {nom}...")
            requete = Request(f"{config.BASE_URL}/{nom}.csv.gz", headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(requete) as reponse, open(chemin, "wb") as f:
                f.write(reponse.read())

def load_tables():
    """Lit les tables téléchargées et les renvoie dans un dictionnaire de DataFrames."""
    return {nom: pd.read_csv(config.RAW_DIR / f"{nom}.csv.gz") for nom in TABLES}


STATS = {
    "matches": ("game_id", "count"),
    "minutes": ("minutes_played", "sum"),
    "goals": ("goals", "sum"),
    "assists": ("assists", "sum"),
    "yellow_cards": ("yellow_cards", "sum"),
    "red_cards": ("red_cards", "sum"),
}


def aggregate_performances(appearances):
    """Somme les matchs de chaque joueur, saison par saison (toutes compétitions confondues).

    Renvoie une ligne par joueur, avec des colonnes du type `minutes_2025_26`
    pour chaque saison de config.SEASONS, et `minutes_total` sur l'ensemble des saisons.
    """
    matchs = appearances.copy()
    matchs["date"] = pd.to_datetime(matchs["date"])

    # On associe à chaque match la saison à laquelle il appartient
    matchs["season"] = None
    for nom, (debut, fin) in config.SEASONS.items():
        dans_saison = matchs["date"].between(debut, fin)
        matchs.loc[dans_saison, "season"] = nom
    matchs = matchs.dropna(subset=["season"])

    # Agrégation par joueur et par saison, puis passage en format large
    par_saison = matchs.groupby(["player_id", "season"]).agg(**STATS)
    large = par_saison.unstack("season")
    large.columns = [f"{stat}_{saison}" for stat, saison in large.columns]

    # Total sur toutes les saisons
    total = matchs.groupby("player_id").agg(**STATS).add_suffix("_total")

    return large.join(total).reset_index()


def build_snapshot(tables):
    """Construit le tableau final : une ligne par joueur.

    Pour chaque joueur évoluant dans un des championnats de config.LEAGUES : sa valeur
    marchande à la date de référence, ses caractéristiques (poste, âge, nationalité, club)
    et ses performances sur chacune des saisons de config.SEASONS.
    """
    ref = pd.Timestamp(config.REFERENCE_DATE)

    # 1. Dernière valeur marchande de chaque joueur avant la date de référence
    valeurs = tables["player_valuations"].copy()
    valeurs["date"] = pd.to_datetime(valeurs["date"])
    valeurs = valeurs[valeurs["date"] <= ref]
    valeurs = valeurs.sort_values("date").groupby("player_id").tail(1)

    # On écarte les valeurs nulles ou trop anciennes
    valeurs = valeurs[valeurs["market_value_in_eur"] > 0]
    anciennete = (ref - valeurs["date"]).dt.days
    valeurs = valeurs[anciennete <= config.MAX_VALUATION_AGE_DAYS]

    valeurs = valeurs[["player_id", "date", "market_value_in_eur", "current_club_id"]]
    valeurs = valeurs.rename(columns={"date": "valuation_date", "current_club_id": "club_id"})

    # 2. Performances : une colonne par statistique et par saison, plus le total
    performances = aggregate_performances(tables["appearances"])

    # 3. Caractéristiques des joueurs et des clubs
    joueurs = tables["players"][
        ["player_id", "name", "position", "sub_position", "foot", "height_in_cm",
         "country_of_citizenship", "date_of_birth"]
    ]
    clubs = tables["clubs"][["club_id", "name", "domestic_competition_id"]]
    clubs = clubs.rename(columns={"name": "club_name"})

    # 4. Fusion des tables (une ligne par joueur)
    df = valeurs.merge(joueurs, on="player_id")
    df = df.merge(clubs, on="club_id", how="left")
    df = df[df["domestic_competition_id"].isin(config.LEAGUES)]  # championnats étudiés
    df = df.merge(performances, on="player_id", how="left")  # NaN = aucun match dans la base

    # 5. Âge à la date de référence
    naissance = pd.to_datetime(df["date_of_birth"])
    df["age"] = (ref - naissance).dt.days // 365.25

    return df.sort_values("market_value_in_eur", ascending=False).reset_index(drop=True)


def save_snapshot(df):
    """Enregistre le tableau final en Parquet dans data/processed/."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.SNAPSHOT_PATH, index=False)


def load_snapshot():
    """Charge le tableau final : fichier local s'il existe, sinon URL publique du bucket.

    C'est la fonction à appeler dans les notebooks.
    """
    if config.SNAPSHOT_PATH.exists():
        return pd.read_parquet(config.SNAPSHOT_PATH)
    if config.SNAPSHOT_URL:
        return pd.read_parquet(config.SNAPSHOT_URL)
    raise FileNotFoundError(
        "Snapshot introuvable. Renseignez SNAPSHOT_URL (voir README) "
        "ou lancez `python scripts/01_collect_transfermarkt.py`."
    )
