# Valeur marchande des joueurs de football et note EA FC 27

Projet du cours *Python pour la data science* (ENSAE).

**Question :** dans quelle mesure les performances et les caractéristiques des joueurs
(poste, âge, club, nationalité) expliquent-elles leur valeur marchande, et ces facteurs
sont-ils les mêmes que ceux qui déterminent leur note dans EA FC 27 ?

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Données

Les données ne sont pas dans Git. Le projet repose sur un fichier daté, `players_snapshot.parquet`
(une ligne par joueur : valeur marchande à la date de référence, caractéristiques, performances de la saison).

**Construire le fichier depuis la source :**

```bash
python scripts/01_collect_transfermarkt.py
```

Le script télécharge 4 tables dans `data/raw/` puis écrit le résultat dans `data/processed/`.
La source est mise à jour chaque semaine : une reconstruction ultérieure peut donner des chiffres
légèrement différents. Pour figer les données, le fichier final est déposé sur un bucket du SSP Cloud
(URL publique à renseigner dans `SNAPSHOT_URL`, variable d'environnement ou `config.py`).

**Dans un notebook :**

```python
from valeur_marchande.transfermarkt import load_snapshot

df = load_snapshot()
```

Les paramètres de l'étude (date de référence, saison) sont dans `src/valeur_marchande/config.py`.

## Sources

- Valeurs marchandes, caractéristiques et statistiques de match : [Transfermarkt](https://www.transfermarkt.com),
  via les tables compilées par [dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets).
- Notes des joueurs : base officielle d'EA SPORTS FC 27 (à collecter).

## Organisation

```
src/valeur_marchande/   fonctions réutilisables (config, collecte)
scripts/                étapes lancées en ligne de commande
notebooks/              exploration et rapport final
data/                   données locales (ignorées par Git)
```
