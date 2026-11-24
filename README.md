# Valeur marchande des joueurs de football et notes EA SPORTS FC

Projet du cours *Python pour la data science* (ENSAE).

**Question :** les performances réelles et les caractéristiques des joueurs (âge, poste, championnat)
expliquent-elles leur valeur marchande, et la note EA SPORTS FC (FIFA 23 à FC 27) récompense-t-elle
les mêmes choses ?

## Par où commencer

- **[`rapport.ipynb`](rapport.ipynb) : le rapport** (problématique, données, résultats, conclusion).
- [`notebooks/analyse_valeur.ipynb`](notebooks/analyse_valeur.ipynb) : analyse détaillée de la valeur marchande.
- [`notebooks/analyse_fifa.ipynb`](notebooks/analyse_fifa.ipynb) : notes FIFA et comparaison avec la valeur.
- [`notebooks/exploration.ipynb`](notebooks/exploration.ipynb) : premiers contrôles des données.

**En bref :** la note FIFA et la valeur marchande sont fortement liées, mais la valeur dépend surtout
du championnat et de l'âge. À note égale, le marché valorise beaucoup plus les jeunes et beaucoup moins
les plus de 30 ans : la note mesure le niveau actuel, la valeur paie aussi l'avenir.

## Installation

Python 3.13 :

```bash
uv sync                    # recommandé (installé sur le SSP Cloud)
# ou : python -m venv .venv, activer l'environnement, puis pip install -e . ipykernel
```

## Données

Aucune donnée n'est dans Git et aucun compte n'est nécessaire : les fichiers bruts et les tableaux
finaux sont figés sur le stockage public du SSP Cloud
(<https://minio.lab.sspcloud.fr/iseo/diffusion/projet_python_football/>), où les notebooks les lisent
automatiquement. Pour reconstruire les tableaux dans `data/` :

```bash
python scripts/01_collect_transfermarkt.py   # valeurs, joueurs, matchs -> snapshot et panel
python scripts/02_collect_ea_fc.py           # notes FIFA, rapprochées des joueurs Transfermarkt
```

Avec `--source`, les scripts collectent à la source au lieu de la copie figée (les chiffres peuvent
alors changer ; Kaggle demande une clé dans `~/.kaggle/access_token`).

**Sources :** [Transfermarkt](https://www.transfermarkt.com) via
[dcaribou/transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) ;
[site des notes d'EA SPORTS FC](https://www.ea.com/games/ea-sports-fc/ratings) (FC 26, FC 27) ;
bases Kaggle [stefanoleone992](https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset)
(FIFA 23, FC 24) et [nyagami](https://www.kaggle.com/datasets/nyagami/ea-sports-fc-25-database-ratings-and-stats) (FC 25).

## Organisation

```
rapport.ipynb           rapport final
notebooks/              analyses détaillées et exploration
src/valeur_marchande/   collecte, nettoyage, rapprochement et fonctions d'analyse
scripts/                étapes de collecte en ligne de commande
data/                   données locales (ignorées par Git)
```
