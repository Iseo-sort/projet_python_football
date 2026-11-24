"""Fonctions et paramètres communs aux notebooks d'analyse."""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

CHAMPIONNATS = {
    "GB1": "Premier League", "ES1": "Liga", "IT1": "Serie A", "L1": "Bundesliga",
    "FR1": "Ligue 1", "NL1": "Eredivisie", "PO1": "Liga Portugal", "BE1": "Pro League",
    "TR1": "Süper Lig",
}
POSTES = {"Goalkeeper": "Gardien", "Defender": "Défenseur", "Midfield": "Milieu",
          "Attack": "Attaquant"}
ORDRE_POSTES = ["Gardien", "Défenseur", "Milieu", "Attaquant"]

# Facteurs des régressions (formules statsmodels), avec Ligue 1 et défenseur comme références
FACTEURS = {
    "Championnat": "C(championnat, Treatment('Ligue 1'))",
    "Âge": "age + I(age ** 2)",
    "Poste": "C(poste, Treatment('Défenseur'))",
    "Temps de jeu": "minutes_milliers",
    "Buts et passes": "buts_10_matchs + passes_10_matchs",
}


def preparer_joueurs(snapshot, minutes_min=900, saison="2025_26"):
    """Garde les joueurs qui ont joué au moins `minutes_min` minutes dans la saison et ajoute
    les variables de l'analyse : noms français, valeur en millions et en log, temps de jeu
    en milliers de minutes, buts et passes décisives pour 10 matchs complets (900 minutes)."""
    joueurs = snapshot.loc[(snapshot[f"minutes_{saison}"] >= minutes_min)
                           & (snapshot["position"] != "Missing")].copy()
    joueurs["championnat"] = joueurs["domestic_competition_id"].map(CHAMPIONNATS)
    joueurs["poste"] = joueurs["position"].map(POSTES)
    joueurs["valeur_millions"] = joueurs["market_value_in_eur"] / 1_000_000
    joueurs["log_valeur"] = np.log(joueurs["market_value_in_eur"])

    minutes = joueurs[f"minutes_{saison}"]
    joueurs["minutes_milliers"] = minutes / 1000
    joueurs["buts_10_matchs"] = joueurs[f"goals_{saison}"] / minutes * 900
    joueurs["passes_10_matchs"] = joueurs[f"assists_{saison}"] / minutes * 900
    return joueurs


def tableau_coefficients(modele, cible_en_log=True):
    """Coefficients d'une régression et leur p-valeur. Si la variable expliquée est un log,
    on ajoute la traduction de chaque coefficient en variation (%) de la variable."""
    tableau = pd.DataFrame({"coefficient": modele.params, "p_valeur": modele.pvalues})
    if cible_en_log:
        tableau["effet_en_pct"] = (np.exp(modele.params) - 1) * 100
    return tableau.drop(index="Intercept").round(3)


def importance_facteurs(donnees, cible, facteurs=FACTEURS):
    """R² perdu quand on retire chaque facteur de la régression complète de `cible`.

    Plus la perte est grande, plus le facteur explique des écarts que les autres
    facteurs n'expliquent pas."""
    complet = smf.ols(f"{cible} ~ " + " + ".join(facteurs.values()), data=donnees).fit()
    lignes = []
    for nom in facteurs:
        autres_termes = [t for n, t in facteurs.items() if n != nom]
        modele_sans = smf.ols(f"{cible} ~ " + " + ".join(autres_termes), data=donnees).fit()
        lignes.append({"facteur": nom, "r2_perdu_si_retire": complet.rsquared - modele_sans.rsquared})
    return pd.DataFrame(lignes)
