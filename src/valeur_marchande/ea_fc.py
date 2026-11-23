"""Collecte des notes des joueurs dans EA SPORTS FC et rapprochement avec Transfermarkt.

Sources, selon l'édition :
- FC 27 (édition en cours) : le site des notes d'EA. Chaque page HTML contient ses données
  dans une balise <script id="__NEXT_DATA__"> : on la lit avec BeautifulSoup ;
- FC 26 : l'API qu'appelle ce site, qui renvoie encore l'édition précédente ;
- FIFA 23, FC 24 et FC 25 : bases publiées sur Kaggle (voir config.KAGGLE_DATASETS).

Toutes les sources utilisent les identifiants de joueurs d'EA (ea_id), qui ne changent
pas d'une édition à l'autre. load_ratings() les met toutes au même format.
"""

import gzip
import json
import re
import time
import unicodedata

import pandas as pd
import requests
from bs4 import BeautifulSoup

from valeur_marchande import config, storage

HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGE_SIZE = 100  # nombre de joueurs par page (maximum accepté par l'API)


def raw_path(edition):
    """Chemin du fichier brut d'une édition, ex. data/raw/ea_fc27_ratings.json.gz
    (JSON pour les sites d'EA, CSV pour les bases Kaggle)."""
    extension = "csv" if edition in config.KAGGLE_DATASETS else "json"
    return config.RAW_DIR / f"ea_{edition}_ratings.{extension}.gz"


def _page_fc27(numero):
    """Une page du site des notes (édition en cours)."""
    reponse = requests.get(config.EA_RATINGS_URL, params={"page": numero},
                           headers=HEADERS, timeout=60)
    reponse.raise_for_status()
    soup = BeautifulSoup(reponse.text, "html.parser")
    page = json.loads(soup.find("script", id="__NEXT_DATA__").string)["props"]["pageProps"]

    # Le site passe à l'édition suivante chaque automne : on vérifie qu'on lit la bonne
    if page["themeSlug"] != "fc-27":
        raise RuntimeError(
            f"Le site affiche l'édition « {page['themeSlug']} » et non FC 27. "
            "Utilisez le fichier brut déjà téléchargé (data/raw) ou celui du bucket."
        )
    return page["ratingDetails"]


def _page_fc26(numero):
    """Une page de l'API des notes (elle renvoie l'édition précédente, FC 26)."""
    params = {"locale": "en", "limit": PAGE_SIZE, "offset": (numero - 1) * PAGE_SIZE}
    reponse = requests.get(config.EA_API_URL, params=params, headers=HEADERS, timeout=60)
    reponse.raise_for_status()
    return reponse.json()


# Fonction de lecture d'une page, pour chaque édition collectée sur les sites d'EA
READERS = {"fc27": _page_fc27, "fc26": _page_fc26}


def download_ratings(edition, from_source=False, pause=1.0):
    """Télécharge toutes les notes d'une édition dans data/raw/, si elles n'y sont pas déjà.

    Par défaut, on prend la copie figée du bucket. Avec from_source=True, on collecte
    depuis la source : les sites d'EA (qui changent d'édition chaque automne) ou Kaggle
    (compte nécessaire). Sites d'EA : on fait une pause entre deux pages pour ne pas
    surcharger le site (≈ 180 à 200 pages, soit 3 à 4 minutes). Le fichier brut (JSON
    compressé) garde tout ce que renvoie le site.
    """
    chemin = raw_path(edition)
    if chemin.exists():
        return
    if not from_source:
        storage.download_from_bucket(chemin)
        return
    if edition in config.KAGGLE_DATASETS:
        _download_kaggle(edition)
        return
    lire_page = READERS[edition]

    premiere = lire_page(1)
    nb_pages = -(-premiere["totalItems"] // PAGE_SIZE)  # division arrondie au-dessus
    joueurs = premiere["items"]
    for numero in range(2, nb_pages + 1):
        time.sleep(pause)
        joueurs += lire_page(numero)["items"]
        if numero % 20 == 0:
            print(f"  {edition} : page {numero}/{nb_pages}")

    # Contrôle : un joueur n'apparaît qu'une fois, et on les a tous
    nb_distincts = len({j["id"] for j in joueurs})
    if nb_distincts != premiere["totalItems"]:
        print(f"Attention : {nb_distincts} joueurs distincts pour {premiere['totalItems']} annoncés.")

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(chemin, "wt", encoding="utf-8") as f:
        json.dump(joueurs, f, ensure_ascii=False)


def _download_kaggle(edition):
    """Télécharge une base Kaggle et garde dans data/raw/ les joueurs de l'édition voulue.

    Il faut un compte Kaggle et sa clé d'accès (fichier ~/.kaggle/access_token ou
    variable d'environnement KAGGLE_API_TOKEN).
    """
    import kagglehub  # importé ici : inutile tant qu'on ne télécharge pas depuis Kaggle

    base, fichier, version = config.KAGGLE_DATASETS[edition]
    dossier = kagglehub.dataset_download(base)
    df = pd.read_csv(f"{dossier}/{fichier}", low_memory=False)
    if version is not None:  # la base stefanoleone992 contient plusieurs éditions
        df = df[df["fifa_version"] == version]

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(raw_path(edition), index=False)


# Colonnes gardées, pour chaque format de source : nom d'origine -> nom dans notre tableau
COLUMNS = {
    # sites d'EA (JSON aplati par json_normalize)
    "ea": {
        "id": "ea_id", "firstName": "ea_first_name", "lastName": "ea_last_name",
        "commonName": "ea_common_name", "birthdate": "ea_birthdate",
        "overallRating": "overall_rating", "position.shortLabel": "ea_position",
        "team.label": "ea_team", "leagueName": "ea_league",
        "nationality.label": "ea_nationality", "preferredFoot": "ea_preferred_foot",
        "skillMoves": "skill_moves", "weakFootAbility": "weak_foot",
        "stats.pac.value": "pace", "stats.sho.value": "shooting", "stats.pas.value": "passing",
        "stats.dri.value": "dribbling", "stats.def.value": "defending",
        "stats.phy.value": "physical",
    },
    # base Kaggle stefanoleone992 (FIFA 23, FC 24)
    "stefanoleone992": {
        "player_id": "ea_id", "long_name": "ea_long_name", "short_name": "ea_common_name",
        "dob": "ea_birthdate", "overall": "overall_rating", "player_positions": "ea_position",
        "club_name": "ea_team", "league_name": "ea_league",
        "nationality_name": "ea_nationality", "preferred_foot": "ea_preferred_foot",
        "skill_moves": "skill_moves", "weak_foot": "weak_foot",
        "pace": "pace", "shooting": "shooting", "passing": "passing",
        "dribbling": "dribbling", "defending": "defending", "physic": "physical",
    },
    # base Kaggle nyagami (FC 25) : pas de date de naissance
    "nyagami": {
        "url": "ea_id", "Name": "ea_common_name", "OVR": "overall_rating",
        "Position": "ea_position", "Team": "ea_team", "League": "ea_league",
        "Nation": "ea_nationality", "Preferred foot": "ea_preferred_foot",
        "Skill moves": "skill_moves", "Weak foot": "weak_foot",
        "PAC": "pace", "SHO": "shooting", "PAS": "passing",
        "DRI": "dribbling", "DEF": "defending", "PHY": "physical",
    },
}


def load_ratings(edition):
    """Lit le fichier brut d'une édition : une ligne par joueur (football masculin),
    avec les mêmes colonnes quelle que soit la source."""
    if edition in config.KAGGLE_DATASETS:
        base = config.KAGGLE_DATASETS[edition][0]
        source = base.split("/")[0]
        df = pd.read_csv(raw_path(edition), low_memory=False)
        df = df[list(COLUMNS[source])].rename(columns=COLUMNS[source])
    else:
        with gzip.open(raw_path(edition), "rt", encoding="utf-8") as f:
            joueurs = json.load(f)
        # json_normalize aplatit le JSON : {"team": {"label": ...}} devient "team.label"
        df = pd.json_normalize(joueurs)
        df = df[df["gender.id"] == 0]  # 0 = football masculin
        df = df[list(COLUMNS["ea"])].rename(columns=COLUMNS["ea"])
        source = "ea"

    if source == "ea":
        df["ea_preferred_foot"] = df["ea_preferred_foot"].map({1: "right", 2: "left"})
        # Date au format américain, suivie d'une heure à ignorer : « 7/13/2007 0:00 »
        df["ea_birthdate"] = df["ea_birthdate"].str.split(" ").str[0]
        df["ea_birthdate"] = pd.to_datetime(df["ea_birthdate"], format="%m/%d/%Y")
    elif source == "stefanoleone992":
        # Seul le nom complet est donné : « Kylian Mbappé Lottin » -> prénom + nom
        df["ea_first_name"] = df["ea_long_name"].str.split(" ").str[0]
        df["ea_last_name"] = df["ea_long_name"].str.split(" ", n=1).str[1]
        # Nom court : utile comme nom d'usage (« Pedri ») mais pas s'il est abrégé (« K. Mbappé »)
        abrege = df["ea_common_name"].str.contains(".", regex=False)
        df["ea_common_name"] = df["ea_common_name"].mask(abrege)
        df["ea_birthdate"] = pd.to_datetime(df["ea_birthdate"])
        df["ea_position"] = df["ea_position"].str.split(",").str[0]
        df = df.drop(columns="ea_long_name")
    elif source == "nyagami":
        # Identifiant EA : à la fin de l'adresse de la fiche du joueur
        df["ea_id"] = df["ea_id"].str.extract(r"/(\d+)$", expand=False).astype(int)
        df["ea_birthdate"] = pd.NaT
    df["ea_preferred_foot"] = df["ea_preferred_foot"].str.lower()

    df = df.reindex(columns=["ea_id"] + [c for c in STANDARD_COLUMNS if c != "ea_id"])
    df.insert(0, "edition", edition)
    return df.reset_index(drop=True)


# Colonnes du tableau renvoyé par load_ratings (dans cet ordre)
STANDARD_COLUMNS = ["ea_id", "ea_first_name", "ea_last_name", "ea_common_name", "ea_birthdate",
                    "overall_rating", "ea_position", "ea_team", "ea_league", "ea_nationality",
                    "ea_preferred_foot", "skill_moves", "weak_foot", "pace", "shooting",
                    "passing", "dribbling", "defending", "physical"]


# --- Rapprochement avec Transfermarkt -------------------------------------------------

# Lettres que la suppression des accents ne transforme pas (elles disparaîtraient)
TRANSLITTERATION = str.maketrans({"đ": "dj", "Đ": "Dj", "ø": "o", "Ø": "O", "ß": "ss",
                                  "æ": "ae", "Æ": "Ae", "ł": "l", "Ł": "L", "ı": "i"})


def name_tokens(texte):
    """Découpe un nom en mots, sans accents ni majuscules : « Đorđe Petrović » -> [djordje, petrovic]."""
    if not isinstance(texte, str):
        return []
    texte = unicodedata.normalize("NFKD", texte.translate(TRANSLITTERATION))
    texte = texte.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", texte).split()


# Règles de rapprochement, de la plus sûre (0) à la plus fragile
RULE_PRIORITY = {"common": 0, "last+first": 0, "last+initial": 1, "last": 2, "single": 2}
MAX_BIRTHDATE_GAP_DAYS = 2  # EA décale parfois la date de naissance d'un ou deux jours


def _first_name_level(prenoms_ea, mots_tm):
    """Compare le prénom EA au nom Transfermarkt.

    Renvoie « first » (prénom identique), « initial » (même initiale, ou diminutif comme
    « maxi » dans « maximiliano ») ou None (prénoms différents).
    """
    if not prenoms_ea or not mots_tm or set(prenoms_ea) & set(mots_tm):
        return "first"
    if prenoms_ea[0][0] == mots_tm[0][0]:
        return "initial"
    if any(p in m or m in p for p in prenoms_ea for m in mots_tm if len(p) >= 3 and len(m) >= 3):
        return "initial"
    return None


def match_rule(candidat):
    """Règle par laquelle un joueur Transfermarkt et un joueur EA (nés à la même date,
    à quelques jours près) sont reconnus comme la même personne, ou None.

    `candidat` est une ligne du tableau des candidats (colonnes Transfermarkt et EA).

    - « common » : le nom d'usage EA (« Lamine Yamal », « Patati ») est dans le nom Transfermarkt ;
    - « last+first » : même nom de famille et même prénom ;
    - « last+initial » : même nom de famille, prénom de même initiale ou diminutif ;
    - « last » : même nom de famille (au moins son dernier mot) mais prénoms différents
      (« Frank » / « André-Franck ») ;
    - « single » : nom Transfermarkt en un seul mot (« Talisca »), présent dans le nom EA,
      et même nationalité.
    Les deux dernières règles, plus fragiles, ne servent que s'il n'y a pas mieux
    (et « last » seulement avec la date de naissance exacte, voir match_players).
    """
    mots_tm = name_tokens(candidat["name"])
    usage = name_tokens(candidat["ea_common_name"])
    if usage and (set(usage) <= set(mots_tm) or "".join(usage) == "".join(mots_tm)):
        return "common"

    noms = [m for m in name_tokens(candidat["ea_last_name"]) if m not in ("da", "de", "dos")]
    prenoms = name_tokens(candidat["ea_first_name"])
    if set(noms) & set(mots_tm):
        niveau = _first_name_level(prenoms, mots_tm)
        if niveau == "first":
            return "last+first"
        if niveau == "initial":
            return "last+initial"
        # Prénoms différents : on exige au moins le dernier mot du nom de famille (dans les
        # bases Kaggle, le « nom » contient parfois des prénoms secondaires : « Daniel
        # Maestro Puch » ne doit pas être rattaché à Daniel Jebbison)
        if noms[-1] in mots_tm:
            return "last"

    tous_ea = set(noms) | set(prenoms) | set(usage)
    meme_nationalite = candidat["country_of_citizenship"] == candidat["ea_nationality"]
    if len(mots_tm) == 1 and mots_tm[0] in tous_ea and meme_nationalite:
        return "single"
    return None


def match_players(joueurs_tm, notes):
    """Associe chaque joueur Transfermarkt à son identifiant EA.

    `joueurs_tm` : colonnes player_id, name, date_of_birth, country_of_citizenship.
    `notes` : tableau renvoyé par load_ratings().

    1. Candidats : joueurs EA nés le même jour, à MAX_BIRTHDATE_GAP_DAYS près.
    2. Chaque candidat reçoit une règle (match_rule) et un score : priorité de la règle,
       puis écart de date. Plus le score est bas, plus le rapprochement est sûr.
    3. On garde le candidat de plus petit score. En cas d'égalité (ex. deux jumeaux de même
       initiale), le joueur n'est pas apparié ; de même si un joueur EA est retenu pour
       plusieurs joueurs Transfermarkt.

    Renvoie : player_id, ea_id, match_rule, birthdate_gap_days.
    """
    tm = joueurs_tm[["player_id", "name", "date_of_birth", "country_of_citizenship"]].copy()
    tm["dob"] = pd.to_datetime(tm["date_of_birth"]).dt.normalize()

    # 1. Candidats : même date de naissance, à quelques jours près
    candidats = []
    for ecart in range(-MAX_BIRTHDATE_GAP_DAYS, MAX_BIRTHDATE_GAP_DAYS + 1):
        decale = notes.assign(dob=notes["ea_birthdate"] - pd.Timedelta(days=ecart))
        candidats.append(tm.merge(decale, on="dob").assign(birthdate_gap_days=abs(ecart)))
    candidats = pd.concat(candidats, ignore_index=True)

    # 2. Règle et score de chaque candidat
    candidats["match_rule"] = candidats.apply(match_rule, axis=1)
    candidats = candidats.dropna(subset=["match_rule"])
    # (nom de famille seul : seulement avec la date de naissance exacte)
    candidats = candidats[(candidats["match_rule"] != "last")
                          | (candidats["birthdate_gap_days"] == 0)]
    candidats["score"] = (10 * candidats["match_rule"].map(RULE_PRIORITY)
                          + candidats["birthdate_gap_days"])

    # 3. Meilleur candidat de chaque joueur, sans égalité
    meilleur_score = candidats.groupby("player_id")["score"].transform("min")
    meilleurs = candidats[candidats["score"] == meilleur_score]
    meilleurs = meilleurs[~meilleurs["player_id"].duplicated(keep=False)]
    meilleurs = meilleurs[~meilleurs["ea_id"].duplicated(keep=False)]

    colonnes = ["player_id", "ea_id", "match_rule", "birthdate_gap_days"]
    return meilleurs[colonnes].reset_index(drop=True)


def build_matched(joueurs_tm, editions):
    """Notes EA des joueurs Transfermarkt : une ligne par joueur apparié et par édition.

    1. Pour chaque édition qui donne la date de naissance : rapprochement par date et nom
       (match_players).
    2. Les identifiants EA ne changent pas d'une édition à l'autre : on en déduit une table
       de passage player_id <-> ea_id (sans les cas où un joueur aurait deux identifiants).
    3. Chaque édition est complétée grâce à cette table (règle « ea_id ») : c'est ainsi
       qu'on apparie FC 25, qui ne donne pas la date de naissance, et les joueurs dont le
       nom a changé d'une édition à l'autre.

    Colonnes : edition, player_id (Transfermarkt), règle et écart de date du
    rapprochement, puis toutes les colonnes de load_ratings().
    """
    notes = {edition: load_ratings(edition) for edition in editions}

    # 1. Date de naissance et nom
    par_nom = {edition: match_players(joueurs_tm, df) for edition, df in notes.items()
               if df["ea_birthdate"].notna().any()}

    # 2. Table de passage player_id <-> ea_id
    passage = pd.concat(par_nom.values())[["player_id", "ea_id"]].drop_duplicates()
    passage = passage[~passage["player_id"].duplicated(keep=False)
                      & ~passage["ea_id"].duplicated(keep=False)]

    # 3. Complément par identifiant EA, édition par édition
    tableaux = []
    for edition, df in notes.items():
        trouves = par_nom.get(edition, passage.iloc[:0])
        complement = passage[passage["ea_id"].isin(df["ea_id"])
                             & ~passage["player_id"].isin(trouves["player_id"])
                             & ~passage["ea_id"].isin(trouves["ea_id"])]
        complement = complement.assign(match_rule="ea_id")
        correspondances = pd.concat([trouves, complement], ignore_index=True)
        tableaux.append(correspondances.merge(df, on="ea_id"))

    df = pd.concat(tableaux, ignore_index=True)
    premieres = ["edition", "player_id"]
    return df[premieres + [c for c in df.columns if c not in premieres]]


def add_ratings_to_panel(panel, notes):
    """Ajoute au panel la note EA en début et en fin de chaque saison.

    Une édition sort en septembre et reflète la saison précédente : pour la saison
    2025-26, la note de début est celle de FC 26 (sortie en septembre 2025) et la note
    de fin celle de FC 27 (septembre 2026). Voir config.EA_EDITIONS.
    """
    notes = notes[["edition", "player_id", "overall_rating"]]
    annee_debut = panel["season"].str[:4].astype(int)
    df = panel.assign(edition_start=annee_debut.map(config.EA_EDITIONS),
                      edition_end=(annee_debut + 1).map(config.EA_EDITIONS))
    for moment in ("start", "end"):
        df = df.merge(
            notes.rename(columns={"edition": f"edition_{moment}",
                                  "overall_rating": f"rating_{moment}"}),
            on=["player_id", f"edition_{moment}"], how="left",
        )
    df["rating_change"] = df["rating_end"] - df["rating_start"]
    return df


def save_matched(df):
    """Enregistre les notes appariées en Parquet dans data/processed/."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.EA_MATCHED_PATH, index=False)


def load_matched(edition=None):
    """Charge les notes EA appariées (toutes les éditions, ou une seule).

    Fichier local s'il existe, sinon copie du bucket.
    """
    df = storage.read_parquet(config.EA_MATCHED_PATH)
    if edition is not None:
        df = df[df["edition"] == edition].reset_index(drop=True)
    return df
