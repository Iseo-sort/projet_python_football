# Valeur marchande des joueurs de football et note EA FC 27

Projet du cours *Python pour la data science* (ENSAE).

**Question :** dans quelle mesure les performances et les caractéristiques des joueurs
(poste, âge, club, nationalité) expliquent-elles leur valeur marchande, et ces facteurs
sont-ils les mêmes que ceux qui déterminent leur note dans EA FC 27 ?

## Installation

Le projet demande Python 3.13 (comme le cours).

**Avec `uv`** (recommandé, déjà installé sur le SSP Cloud) :

```bash
uv sync                      # crée .venv et installe le projet et ses dépendances
source .venv/bin/activate    # ou préfixer les commandes par `uv run`
```

**Avec `pip`** :

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Données

Les données ne sont pas dans Git. Le projet repose sur deux fichiers construits à partir de la source :

- `players_snapshot.parquet` : une ligne par joueur, avec sa valeur marchande à la date de référence,
  ses caractéristiques et ses performances saison par saison ;
- `players_panel.parquet` : une ligne par joueur et par saison, avec sa valeur en début et en fin
  de saison, pour étudier les variations de valeur.

Un joueur fait partie de l'étude pour une saison s'il figure sur la feuille d'au moins un match
d'un des championnats étudiés (titulaire ou remplaçant).

**Construire le fichier depuis la source :**

```bash
python scripts/01_collect_transfermarkt.py
```

Le script télécharge les tables de la source dans `data/raw/` puis écrit les deux fichiers dans `data/processed/`.
La source est mise à jour chaque semaine : une reconstruction ultérieure peut donner des chiffres
légèrement différents. Pour figer les données, les fichiers finaux sont déposés sur un bucket du SSP Cloud
(URL publiques à renseigner dans `SNAPSHOT_URL` et `PANEL_URL`, variables d'environnement ou `config.py`).

**Notes EA SPORTS FC :**

```bash
python scripts/02_collect_ea_fc.py
```

Le script récupère les notes sur les sites officiels d'EA (≈ 200 pages par édition, environ 4 minutes
chacune), garde les fichiers bruts dans `data/raw/`, puis associe chaque joueur EA à son identifiant
Transfermarkt et écrit `ea_ratings_matched.parquet` (une ligne par joueur et par édition) dans
`data/processed/`.

| Édition | Note au début de la saison | Source |
|---|---|---|
| FC 27 | 2026-27 (fin de 2025-26) | site des notes d'EA (édition en cours) |
| FC 26 | 2025-26 | API du site des notes (édition précédente) |
| FC 25 | 2024-25 | base Kaggle [nyagami](https://www.kaggle.com/datasets/nyagami/ea-sports-fc-25-database-ratings-and-stats) |
| FIFA 23, FC 24 | 2022-23, 2023-24 | base Kaggle [stefanoleone992](https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset) |

Pour les bases Kaggle, il faut un compte Kaggle et sa clé d'accès (kaggle.com → Settings → API →
*Generate New Token*), à placer **hors du dépôt** :

```bash
mkdir -p ~/.kaggle && echo -n "<votre clé>" > ~/.kaggle/access_token && chmod 600 ~/.kaggle/access_token
```

Le site et l'API d'EA changent d'édition chaque automne : les fichiers bruts déjà téléchargés
doivent donc être conservés (le script s'arrête s'il ne trouve plus FC 27 sur le site).

Le rapprochement se fait sur la date de naissance (à 2 jours près) et le nom (sans accents, nom d'usage,
prénom ou initiale). Toutes les sources utilisent les identifiants de joueurs d'EA, qui ne changent pas
d'une édition à l'autre : ils servent à compléter chaque édition, en particulier FC 25 dont la base ne
donne pas la date de naissance (règle `ea_id`). Environ 84 % des joueurs du snapshot sont associés ; les autres sont surtout des
joueurs à faible valeur ou partis vers un championnat absent du jeu. La colonne `match_rule` indique
la règle utilisée. Contrôle : un même joueur retrouve le même identifiant EA d'une édition à l'autre
dans 99,85 % des cas.

**Dans un notebook :**

```python
from valeur_marchande.transfermarkt import load_snapshot, load_panel

df = load_snapshot()     # une ligne par joueur
panel = load_panel()     # une ligne par joueur et par saison

from valeur_marchande.ea_fc import load_matched, add_ratings_to_panel
notes = load_matched("fc27")                           # à fusionner avec df sur player_id
panel = add_ratings_to_panel(panel, load_matched())    # note en début et fin de saison
```

Les paramètres de l'étude (date de référence, saisons, championnats) sont dans `src/valeur_marchande/config.py`.

## Sources

- Valeurs marchandes, caractéristiques et statistiques de match : [Transfermarkt](https://www.transfermarkt.com),
  via les tables compilées par [dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets).
- Notes des joueurs : [site officiel des notes d'EA SPORTS FC](https://www.ea.com/games/ea-sports-fc/ratings) (FC 26 et FC 27)
  et bases Kaggle de stefanoleone992 (FIFA 23, FC 24) et nyagami (FC 25).

## Organisation

```
src/valeur_marchande/   fonctions réutilisables (config, collecte)
scripts/                étapes lancées en ligne de commande
notebooks/              exploration et rapport final
data/                   données locales (ignorées par Git)
```
