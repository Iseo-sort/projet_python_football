"""Collecte des données Transfermarkt et construction des tableaux d'analyse.

- le snapshot : une ligne par joueur, valeur marchande à la date de référence ;
- le panel : une ligne par joueur et par saison, pour étudier les variations de valeur.
"""

from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from valeur_marchande import config

# Les tables dont on a besoin
TABLES = ["players", "competitions", "player_valuations", "clubs", "appearances",
          "game_lineups"]


def download_tables():
    """Télécharge les tables (fichiers .csv.gz) dans data/raw/, si elles n'y sont pas déjà."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for nom in TABLES:
        chemin = config.RAW_DIR / f"{nom}.csv.gz"
        if not chemin.exists():
            print(f"Téléchargement de {nom}...")
            url = f"{config.BASE_URL}/{nom}.csv.gz"
            requete = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(requete) as reponse, open(chemin, "wb") as f:
                f.write(reponse.read())


def load_tables():
    """Lit les tables téléchargées et les renvoie dans un dictionnaire de DataFrames."""
    return {nom: pd.read_csv(config.RAW_DIR / f"{nom}.csv.gz", low_memory=False)
            for nom in TABLES}


STATS = {
    "matches": ("game_id", "count"),
    "minutes": ("minutes_played", "sum"),
    "goals": ("goals", "sum"),
    "assists": ("assists", "sum"),
    "yellow_cards": ("yellow_cards", "sum"),
    "red_cards": ("red_cards", "sum"),
}

# Caractéristiques des joueurs reprises dans les deux tableaux
PLAYER_COLUMNS = ["player_id", "name", "position", "sub_position", "foot", "height_in_cm",
                  "country_of_citizenship", "date_of_birth"]


def value_at(valuations, date):
    """Valeur marchande de chaque joueur à une date donnée.

    On prend la dernière valeur connue à cette date, en écartant les valeurs nulles ou
    plus vieilles que config.MAX_VALUATION_AGE_DAYS.
    (Les colonnes club et championnat de cette table ne sont pas historiques : elles
    restent souvent figées sur le dernier club suivi par la source. On ne les utilise pas.)
    """
    date = pd.Timestamp(date)
    valeurs = valuations.copy()
    valeurs["date"] = pd.to_datetime(valeurs["date"])
    valeurs = valeurs[valeurs["date"] <= date]
    valeurs = valeurs.sort_values("date").groupby("player_id").tail(1)

    valeurs = valeurs[valeurs["market_value_in_eur"] > 0]
    anciennete = (date - valeurs["date"]).dt.days
    valeurs = valeurs[anciennete <= config.MAX_VALUATION_AGE_DAYS]

    valeurs = valeurs[["player_id", "date", "market_value_in_eur"]]
    return valeurs.rename(columns={"date": "valuation_date"})


def add_season(df):
    """Ajoute une colonne `season` (clé de config.SEASONS) d'après la colonne `date`.

    Les lignes hors des saisons étudiées sont retirées.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["season"] = None
    for nom, (debut, fin) in config.SEASONS.items():
        df.loc[df["date"].between(debut, fin), "season"] = nom
    return df.dropna(subset=["season"])


def league_squads(tables):
    """Club et championnat de chaque joueur, saison par saison.

    Un joueur appartient à un des championnats de config.LEAGUES pour une saison s'il
    figure sur la feuille d'au moins un match de ce championnat (titulaire ou remplaçant,
    même sans entrer en jeu). Son club est celui de son dernier match de championnat
    de la saison (utile en cas de transfert en cours de saison).

    Renvoie une ligne par couple (joueur, saison).
    """
    # Compétition de chaque match (la table des feuilles de match ne la donne pas)
    competitions = tables["appearances"][["game_id", "competition_id"]].drop_duplicates("game_id")

    feuilles = tables["game_lineups"][["game_id", "date", "player_id", "club_id"]]
    feuilles = feuilles.merge(competitions, on="game_id")
    feuilles = feuilles[feuilles["competition_id"].isin(config.LEAGUES)]
    feuilles = add_season(feuilles)

    dernier = feuilles.sort_values("date").groupby(["player_id", "season"]).tail(1)
    dernier = dernier.rename(columns={"competition_id": "domestic_competition_id"})
    return dernier[["player_id", "season", "club_id", "domestic_competition_id"]]


def performances_by_season(appearances):
    """Somme les matchs de chaque joueur, saison par saison (toutes compétitions confondues).

    Renvoie une ligne par couple (joueur, saison), pour les saisons de config.SEASONS.
    """
    matchs = add_season(appearances)
    return matchs.groupby(["player_id", "season"]).agg(**STATS).reset_index()


def aggregate_performances(appearances):
    """Performances en format large : une ligne par joueur.

    Colonnes du type `minutes_2025_26` pour chaque saison de config.SEASONS,
    et `minutes_total` sur l'ensemble des saisons.
    """
    par_saison = performances_by_season(appearances).set_index(["player_id", "season"])
    large = par_saison.unstack("season")
    large.columns = [f"{stat}_{saison}" for stat, saison in large.columns]

    # Total sur toutes les saisons
    total = par_saison.groupby("player_id").sum().add_suffix("_total")

    return large.join(total).reset_index()


def club_names(tables):
    """Table de correspondance identifiant du club -> nom du club."""
    return tables["clubs"][["club_id", "name"]].rename(columns={"name": "club_name"})


def season_of(date):
    """Saison de config.SEASONS qui contient la date donnée."""
    date = pd.Timestamp(date)
    for nom, (debut, fin) in config.SEASONS.items():
        if pd.Timestamp(debut) <= date <= pd.Timestamp(fin):
            return nom
    raise ValueError(f"La date {date.date()} n'est dans aucune saison de config.SEASONS")


def build_snapshot(tables):
    """Construit le tableau final : une ligne par joueur.

    Pour chaque joueur figurant sur une feuille de match d'un des championnats de
    config.LEAGUES pendant la saison de la date de référence : sa valeur marchande à
    cette date, ses caractéristiques (poste, âge, nationalité, club) et ses performances
    sur chacune des saisons de config.SEASONS.
    """
    ref = pd.Timestamp(config.REFERENCE_DATE)

    # 1. Joueurs des championnats étudiés pendant la saison de référence, et leur club
    effectifs = league_squads(tables)
    effectifs = effectifs[effectifs["season"] == season_of(ref)].drop(columns="season")

    # 2. Leur valeur marchande à la date de référence
    df = value_at(tables["player_valuations"], ref).merge(effectifs, on="player_id")

    # 3. Caractéristiques des joueurs et nom des clubs
    df = df.merge(tables["players"][PLAYER_COLUMNS], on="player_id")
    df = df.merge(club_names(tables), on="club_id", how="left")

    # 4. Performances : une colonne par statistique et par saison, plus le total
    #    (aucun match joué dans la base sur une saison = 0)
    performances = aggregate_performances(tables["appearances"])
    df = df.merge(performances, on="player_id", how="left")
    colonnes_perf = performances.columns.drop("player_id")
    df[colonnes_perf] = df[colonnes_perf].fillna(0).astype(int)

    # 5. Âge à la date de référence
    naissance = pd.to_datetime(df["date_of_birth"])
    df["age"] = (ref - naissance).dt.days // 365.25

    return df.sort_values("market_value_in_eur", ascending=False).reset_index(drop=True)


def build_panel(tables):
    """Construit le tableau « joueur x saison » pour étudier les variations de valeur.

    Une ligne par joueur et par saison de config.SEASONS, pour tous les joueurs qui
    figurent sur une feuille de match d'un des championnats de config.LEAGUES cette
    saison-là (et pas seulement ceux qui y sont encore aujourd'hui, pour éviter un biais
    de survie).

    Pour chaque ligne : la valeur au début de la saison (30 juin précédent) et à la fin
    (30 juin), sa variation en log, le club de la saison, les performances de la saison
    et l'âge au début de la saison. Une valeur absente de la source (ou trop ancienne)
    donne une valeur et une variation manquantes (NaN).
    """
    effectifs = league_squads(tables)
    valuations = tables["player_valuations"]

    lignes = []
    for saison, (debut, fin) in config.SEASONS.items():
        veille = pd.Timestamp(debut) - pd.Timedelta(days=1)
        saison_df = effectifs[effectifs["season"] == saison].copy()
        saison_df["season_start"] = veille

        depart = value_at(valuations, veille).add_suffix("_start")
        arrivee = value_at(valuations, fin).add_suffix("_end")
        saison_df = saison_df.merge(depart, left_on="player_id",
                                    right_on="player_id_start", how="left")
        saison_df = saison_df.merge(arrivee, left_on="player_id",
                                    right_on="player_id_end", how="left")
        lignes.append(saison_df.drop(columns=["player_id_start", "player_id_end"]))

    df = pd.concat(lignes, ignore_index=True)
    df = df.rename(columns={"market_value_in_eur_start": "value_start",
                            "market_value_in_eur_end": "value_end"})
    df["log_value_change"] = np.log(df["value_end"]) - np.log(df["value_start"])

    # Caractéristiques des joueurs, nom des clubs et âge au début de la saison
    df = df.merge(tables["players"][PLAYER_COLUMNS], on="player_id", how="left")
    df = df.merge(club_names(tables), on="club_id", how="left")
    naissance = pd.to_datetime(df["date_of_birth"])
    df["age"] = (df["season_start"] - naissance).dt.days // 365.25

    # Performances de la saison (aucun match joué dans la base = 0)
    performances = performances_by_season(tables["appearances"])
    df = df.merge(performances, on=["player_id", "season"], how="left")
    df[list(STATS)] = df[list(STATS)].fillna(0).astype(int)

    df = df.sort_values(["season", "value_start"], ascending=[True, False])
    return df.reset_index(drop=True)


def save_snapshot(df):
    """Enregistre le snapshot en Parquet dans data/processed/."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.SNAPSHOT_PATH, index=False)


def save_panel(df):
    """Enregistre le panel en Parquet dans data/processed/."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.PANEL_PATH, index=False)


def _load(chemin, url):
    """Charge un tableau : fichier local s'il existe, sinon URL publique du bucket."""
    if chemin.exists():
        return pd.read_parquet(chemin)
    if url:
        return pd.read_parquet(url)
    raise FileNotFoundError(
        f"{chemin.name} introuvable. Renseignez son URL (voir README) "
        "ou lancez `python scripts/01_collect_transfermarkt.py`."
    )


def load_snapshot():
    """Charge le snapshot (une ligne par joueur). À appeler dans les notebooks."""
    return _load(config.SNAPSHOT_PATH, config.SNAPSHOT_URL)


def load_panel():
    """Charge le panel (une ligne par joueur et par saison). À appeler dans les notebooks."""
    return _load(config.PANEL_PATH, config.PANEL_URL)
