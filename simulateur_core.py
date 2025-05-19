import streamlit as st
import pandas as pd
from google.cloud import bigquery
import os
import json
import tempfile

# Lire le JSON de la variable d’environnement (Render)
creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if creds_json:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp:
        tmp.write(creds_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

# Créer le client BigQuery à partir des variables d’environnement
client = bigquery.Client()


def get_type_classement(id_championnat):
    query = f"""
        SELECT CLASSEMENT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        WHERE ID_CHAMPIONNAT = {id_championnat}
        LIMIT 1
    """
    df = client.query(query).to_dataframe()

    if not df.empty and "CLASSEMENT" in df.columns:
        return df.iloc[0]["CLASSEMENT"]
    return "GENERALE"


def get_classement_dynamique(id_championnat, date_limite=None, journee_min=None, journee_max=None, matchs_override=None):
    if matchs_override is not None:
        matchs = matchs_override.copy()
    else:
        # Chargement selon le filtre défini
        if journee_min is not None and journee_max is not None:
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {id_championnat}
                  AND JOURNEE BETWEEN {journee_min} AND {journee_max}
            """
        elif journee_max is not None:
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {id_championnat}
                  AND JOURNEE <= {journee_max}
            """
        elif date_limite is not None:
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {id_championnat}
                  AND DATE <= DATE('{date_limite}')
            """
        else:
            st.warning("❌ Vous devez spécifier une date ou une journée.")
            return pd.DataFrame()

        matchs = client.query(query).to_dataframe()

    # ✅ Sécurité renforcée
    if matchs is None:
        st.warning("❌ Aucun match transmis à get_classement_dynamique (matchs = None)")
        return pd.DataFrame()

    if matchs.empty:
        st.warning("⚠️ matchs transmis vide (0 ligne)")
        return pd.DataFrame()

    st.write("✅ Nombre de matchs pris en compte :", len(matchs))

    match_equipes = pd.concat([
        matchs.assign(
            ID_EQUIPE=matchs["ID_EQUIPE_DOM"],
            NOM_EQUIPE=matchs["EQUIPE_DOM"],
            BUTS_POUR=matchs["NB_BUT_DOM"],
            BUTS_CONTRE=matchs["NB_BUT_EXT"],
            POINTS=matchs.apply(
                lambda row: 3 if row["NB_BUT_DOM"] > row["NB_BUT_EXT"]
                else (1 if row["NB_BUT_DOM"] == row["NB_BUT_EXT"] else 0),
                axis=1,
            )
        ),
        matchs.assign(
            ID_EQUIPE=matchs["ID_EQUIPE_EXT"],
            NOM_EQUIPE=matchs["EQUIPE_EXT"],
            BUTS_POUR=matchs["NB_BUT_EXT"],
            BUTS_CONTRE=matchs["NB_BUT_DOM"],
            POINTS=matchs.apply(
                lambda row: 3 if row["NB_BUT_EXT"] > row["NB_BUT_DOM"]
                else (1 if row["NB_BUT_EXT"] == row["NB_BUT_DOM"] else 0),
                axis=1,
            )
        )
    ])

    classement = match_equipes.groupby(["POULE", "ID_EQUIPE", "NOM_EQUIPE"]).agg(
        MJ=('ID_EQUIPE', 'count'),
        G=('POINTS', lambda x: (x == 3).sum()),
        N=('POINTS', lambda x: (x == 1).sum()),
        P=('POINTS', lambda x: (x == 0).sum()),
        BP=('BUTS_POUR', 'sum'),
        BC=('BUTS_CONTRE', 'sum'),
        POINTS=('POINTS', 'sum'),
    ).reset_index()

    classement["DIFF"] = classement["BP"] - classement["BC"]

    return classement

def get_matchs_termine(id_championnat, date_limite=None, journee_min=None, journee_max=None):
    if journee_min is not None and journee_max is not None:
        query = f"""
            SELECT *
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE STATUT = 'TERMINE'
              AND ID_CHAMPIONNAT = {id_championnat}
              AND JOURNEE BETWEEN {journee_min} AND {journee_max}
        """
    elif journee_max is not None:
        query = f"""
            SELECT *
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE STATUT = 'TERMINE'
              AND ID_CHAMPIONNAT = {id_championnat}
              AND JOURNEE <= {journee_max}
        """
    elif date_limite is not None:
        query = f"""
            SELECT *
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE STATUT = 'TERMINE'
              AND ID_CHAMPIONNAT = {id_championnat}
              AND DATE <= DATE('{date_limite}')
        """
    else:
        st.warning("❌ Vous devez spécifier une date ou une plage de journées.")
        return pd.DataFrame()

    return client.query(query).to_dataframe()


def appliquer_diff_particuliere(classement_df, matchs_df, selected_poule="Toutes les poules"):
    classement_df["RANG_CONFRONT"] = 999
    mini_classements = {}

    groupes = classement_df.copy()
    groupes = groupes[groupes.duplicated(subset=["POULE", "POINTS"], keep=False)]
    groupes = groupes.groupby(["POULE", "POINTS"])

    for (poule, pts), groupe in groupes:
        if selected_poule != "Toutes les poules" and poule != selected_poule:
            continue

        equipes_concernees = groupe["ID_EQUIPE"].tolist()

        matchs_confrontations = matchs_df[
            (matchs_df["ID_EQUIPE_DOM"].isin(equipes_concernees)) &
            (matchs_df["ID_EQUIPE_EXT"].isin(equipes_concernees))
        ]

        mini_classement = []
        for equipe_id in equipes_concernees:
            matchs_eq = matchs_confrontations[
                (matchs_confrontations["ID_EQUIPE_DOM"] == equipe_id) |
                (matchs_confrontations["ID_EQUIPE_EXT"] == equipe_id)
            ]

            points = 0
            diff_buts = 0
            for _, row in matchs_eq.iterrows():
                if row["ID_EQUIPE_DOM"] == equipe_id:
                    bp, bc = row["NB_BUT_DOM"], row["NB_BUT_EXT"]
                else:
                    bp, bc = row["NB_BUT_EXT"], row["NB_BUT_DOM"]

                if bp > bc:
                    points += 3
                elif bp == bc:
                    points += 1
                diff_buts += bp - bc

            nom_equipe = groupe[groupe["ID_EQUIPE"] == equipe_id]["NOM_EQUIPE"].values[0]
            mini_classement.append({
                "ID_EQUIPE": equipe_id,
                "NOM_EQUIPE": nom_equipe,
                "PTS_CONFRONT": points,
                "DIFF_CONFRONT": diff_buts
            })

        mini_df = pd.DataFrame(mini_classement)
        mini_df = mini_df.sort_values(by=["PTS_CONFRONT", "DIFF_CONFRONT"], ascending=[False, False])
        mini_df["RANG_CONFRONT"] = range(1, len(mini_df) + 1)

        for _, row in mini_df.iterrows():
            classement_df.loc[classement_df["ID_EQUIPE"] == row["ID_EQUIPE"], "RANG_CONFRONT"] = row["RANG_CONFRONT"]

        mini_classements[(poule, pts)] = {
            "classement": mini_df.drop(columns=["ID_EQUIPE"]),
            "matchs": matchs_confrontations[["DATE", "EQUIPE_DOM", "EQUIPE_EXT", "NB_BUT_DOM", "NB_BUT_EXT"]].sort_values("DATE")
        }

    return classement_df, mini_classements

def get_poules_temp(id_championnat):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {id_championnat}
          AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()


def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU, CLASSEMENT, NBRE_JOURNEES
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
    """
    return client.query(query).to_dataframe()

def appliquer_penalites(classement_df, date_limite=None):
    if date_limite is None:
        st.warning("⚠️ Pénalités ignorées : aucune date limite fournie.")
        classement_df["PENALITES"] = 0
        return classement_df

    penalites_query = f"""
        SELECT ID_EQUIPE, SUM(POINTS) AS PENALITES
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_PENALITE`
        WHERE DATE <= DATE('{date_limite}')
        GROUP BY ID_EQUIPE
    """
    df_penalites = client.query(penalites_query).to_dataframe()

    classement_df = classement_df.merge(df_penalites, on="ID_EQUIPE", how="left")
    classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0).astype(int)
    classement_df["POINTS"] = classement_df["POINTS"] - classement_df["PENALITES"]

    return classement_df


def trier_et_numeroter(classement_df, type_classement):
    if type_classement == "PARTICULIERE":
        classement_df["RANG_CONFRONT"] = classement_df.get("RANG_CONFRONT", 999)
        classement_df = classement_df.sort_values(
            by=["POULE", "POINTS", "RANG_CONFRONT", "DIFF", "BP"],
            ascending=[True, False, True, False, False]
        )
    else:
        classement_df = classement_df.sort_values(
            by=["POULE", "POINTS", "DIFF", "BP"],
            ascending=[True, False, False, False]
        )
    classement_df["CLASSEMENT"] = classement_df.groupby("POULE").cumcount() + 1
    return classement_df

def classement_special_u19(classement_df, id_championnat, date_limite=None, journee_min=None, journee_max=None):
    if id_championnat != 6 or classement_df.empty:
        return None

    # Choix du filtre SQL
    if journee_min is not None and journee_max is not None:
        filtre = f"AND JOURNEE BETWEEN {journee_min} AND {journee_max}"
    elif date_limite is not None:
        filtre = f"AND DATE <= DATE('{date_limite}')"
    else:
        st.warning("❌ Aucun filtre valide fourni pour le calcul du comparatif U19.")
        return None

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {id_championnat}
          {filtre}
    """
    matchs_u19 = client.query(query).to_dataframe()

    df_11e = classement_df[classement_df["CLASSEMENT"] == 11]
    comparatif_11e = []

    for _, row in df_11e.iterrows():
        poule = row["POULE"]
        equipe_11e = row["NOM_EQUIPE"]
        adversaires = classement_df[
            (classement_df["POULE"] == poule) &
            (classement_df["CLASSEMENT"].between(6, 10))
        ]["NOM_EQUIPE"].tolist()

        confrontations = matchs_u19[
            ((matchs_u19["EQUIPE_DOM"] == equipe_11e) & (matchs_u19["EQUIPE_EXT"].isin(adversaires))) |
            ((matchs_u19["EQUIPE_EXT"] == equipe_11e) & (matchs_u19["EQUIPE_DOM"].isin(adversaires)))
        ]

        pts = 0
        for _, m in confrontations.iterrows():
            if m["EQUIPE_DOM"] == equipe_11e:
                pts += 3 if m["NB_BUT_DOM"] > m["NB_BUT_EXT"] else 1 if m["NB_BUT_DOM"] == m["NB_BUT_EXT"] else 0
            elif m["EQUIPE_EXT"] == equipe_11e:
                pts += 3 if m["NB_BUT_EXT"] > m["NB_BUT_DOM"] else 1 if m["NB_BUT_EXT"] == m["NB_BUT_DOM"] else 0

        comparatif_11e.append({"POULE": poule, "EQUIPE": equipe_11e, "PTS_CONFRONT_6_10": pts})

    df_11e_comp = pd.DataFrame(comparatif_11e).sort_values(by="PTS_CONFRONT_6_10", ascending=False)
    df_11e_comp["RANG"] = df_11e_comp["PTS_CONFRONT_6_10"].rank(method="min", ascending=False).astype(int)
    return df_11e_comp


def classement_special_u17(classement_df, id_championnat, date_limite=None, journee_min=None, journee_max=None):
    if id_championnat != 7 or classement_df.empty:
        return None

    df_2e = classement_df[classement_df["CLASSEMENT"] == 2]
    comparatif_2e = []

    for _, row in df_2e.iterrows():
        poule = row["POULE"]
        equipe_2e = row["NOM_EQUIPE"]

        # Sélection des 5 autres équipes les mieux classées (hors 2e)
        top_5 = classement_df[
            (classement_df["POULE"] == poule) &
            (classement_df["NOM_EQUIPE"] != equipe_2e)
        ].sort_values("CLASSEMENT").head(5)["NOM_EQUIPE"].tolist()

        # Choix du filtre selon la configuration
        if journee_min is not None and journee_max is not None:
            filtre = f"AND JOURNEE BETWEEN {journee_min} AND {journee_max}"
        elif date_limite is not None:
            filtre = f"AND DATE <= DATE('{date_limite}')"
        else:
            st.warning("❌ Aucun filtre valide fourni pour la règle spéciale U17.")
            return None

        query = f"""
            SELECT EQUIPE_DOM, EQUIPE_EXT, NB_BUT_DOM, NB_BUT_EXT, DATE
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE ID_CHAMPIONNAT = {id_championnat}
              AND POULE = '{poule}'
              AND STATUT = 'TERMINE'
              {filtre}
        """
        matchs_poule = client.query(query).to_dataframe()

        # Filtrer les confrontations du 2e avec les 5 équipes sélectionnées
        confrontations = matchs_poule[
            ((matchs_poule["EQUIPE_DOM"] == equipe_2e) & (matchs_poule["EQUIPE_EXT"].isin(top_5))) |
            ((matchs_poule["EQUIPE_EXT"] == equipe_2e) & (matchs_poule["EQUIPE_DOM"].isin(top_5)))
        ]

        # Calcul des points obtenus dans ces confrontations
        pts = 0
        for _, m in confrontations.iterrows():
            if m["EQUIPE_DOM"] == equipe_2e:
                if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
            elif m["EQUIPE_EXT"] == equipe_2e:
                if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

        comparatif_2e.append({
            "POULE": poule,
            "EQUIPE": equipe_2e,
            "PTS_CONFRONT_TOP5": pts
        })

    # Création du classement des 2e
    df_2e_comp = pd.DataFrame(comparatif_2e).sort_values("PTS_CONFRONT_TOP5", ascending=False)
    df_2e_comp["RANG"] = df_2e_comp["PTS_CONFRONT_TOP5"].rank(method="min", ascending=False).astype(int)
    return df_2e_comp

def classement_special_n2(classement_df, id_championnat, date_limite=None, journee_min=None, journee_max=None):
    if id_championnat != 4 or classement_df.empty:
        return None

    df_13e = classement_df[classement_df["CLASSEMENT"] == 13]
    comparatif_13e = []

    if journee_min is not None and journee_max is not None:
        filtre = f"AND JOURNEE BETWEEN {journee_min} AND {journee_max}"
    elif date_limite is not None:
        filtre = f"AND DATE <= DATE('{date_limite}')"
    else:
        st.warning("❌ Aucun filtre valide fourni pour la règle spéciale N2.")
        return None

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {id_championnat}
          {filtre}
    """
    matchs_n2 = client.query(query).to_dataframe()

    for _, row in df_13e.iterrows():
        poule = row["POULE"]
        equipe_13e = row["NOM_EQUIPE"]

        adversaires = classement_df[
            (classement_df["POULE"] == poule) &
            (classement_df["CLASSEMENT"].between(8, 12))
        ]["NOM_EQUIPE"].tolist()

        confrontations = matchs_n2[
            ((matchs_n2["EQUIPE_DOM"] == equipe_13e) & (matchs_n2["EQUIPE_EXT"].isin(adversaires))) |
            ((matchs_n2["EQUIPE_EXT"] == equipe_13e) & (matchs_n2["EQUIPE_DOM"].isin(adversaires)))
        ]

        pts = 0
        for _, m in confrontations.iterrows():
            if m["EQUIPE_DOM"] == equipe_13e:
                if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
            elif m["EQUIPE_EXT"] == equipe_13e:
                if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

        comparatif_13e.append({
            "POULE": poule,
            "EQUIPE": equipe_13e,
            "PTS_CONFRONT_8_12": pts
        })

    df_13e_comp = pd.DataFrame(comparatif_13e).sort_values("PTS_CONFRONT_8_12", ascending=False)
    df_13e_comp["RANG"] = df_13e_comp["PTS_CONFRONT_8_12"].rank(method="min", ascending=False).astype(int)
    return df_13e_comp


def classement_special_n3(classement_df, id_championnat, date_limite=None, journee_min=None, journee_max=None):
    if id_championnat != 5 or classement_df.empty:
        return None

    df_10e = classement_df[classement_df["CLASSEMENT"] == 10]
    comparatif_10e = []

    if journee_min is not None and journee_max is not None:
        filtre = f"AND JOURNEE BETWEEN {journee_min} AND {journee_max}"
    elif date_limite is not None:
        filtre = f"AND DATE <= DATE('{date_limite}')"
    else:
        st.warning("❌ Aucun filtre valide fourni pour la règle spéciale N3.")
        return None

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {id_championnat}
          {filtre}
    """
    matchs_n3 = client.query(query).to_dataframe()

    for _, row in df_10e.iterrows():
        poule = row["POULE"]
        equipe_10e = row["NOM_EQUIPE"]

        adversaires = classement_df[
            (classement_df["POULE"] == poule) &
            (classement_df["CLASSEMENT"].between(5, 9))
        ]["NOM_EQUIPE"].tolist()

        confrontations = matchs_n3[
            ((matchs_n3["EQUIPE_DOM"] == equipe_10e) & (matchs_n3["EQUIPE_EXT"].isin(adversaires))) |
            ((matchs_n3["EQUIPE_EXT"] == equipe_10e) & (matchs_n3["EQUIPE_DOM"].isin(adversaires)))
        ]

        pts = 0
        for _, m in confrontations.iterrows():
            if m["EQUIPE_DOM"] == equipe_10e:
                if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
            elif m["EQUIPE_EXT"] == equipe_10e:
                if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

        comparatif_10e.append({
            "POULE": poule,
            "EQUIPE": equipe_10e,
            "PTS_CONFRONT_5_9": pts
        })

    df_10e_comp = pd.DataFrame(comparatif_10e).sort_values("PTS_CONFRONT_5_9", ascending=False)
    df_10e_comp["RANG"] = df_10e_comp["PTS_CONFRONT_5_9"].rank(method="min", ascending=False).astype(int)
    return df_10e_comp

def get_matchs_modifiables(id_championnat, date_limite=None, non_joues_only=True):
    condition_statut = "AND STATUT IS NULL" if non_joues_only else ""
    condition_date = f"AND DATE <= DATE('{date_limite}')" if date_limite else ""

    query = f"""
        SELECT 
            ID_MATCH,
            JOURNEE,
            POULE,
            DATE,
            ID_EQUIPE_DOM,
            EQUIPE_DOM,
            NB_BUT_DOM,
            ID_EQUIPE_EXT,
            EQUIPE_EXT,
            NB_BUT_EXT,
            STATUT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {id_championnat}
          {condition_date}
          {condition_statut}
        ORDER BY DATE, JOURNEE
    """
    return client.query(query).to_dataframe()


def recalculer_classement_simule(matchs_simules, id_championnat, date_limite, selected_poule, type_classement):
    matchs_simules = matchs_simules.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

    matchs_historiques = get_matchs_termine(id_championnat, date_limite)
    matchs_historiques = matchs_historiques[~matchs_historiques["ID_MATCH"].isin(matchs_simules["ID_MATCH"])]

    matchs_complets = pd.concat([matchs_historiques, matchs_simules], ignore_index=True)

    dom = matchs_complets[["POULE", "ID_EQUIPE_DOM", "EQUIPE_DOM", "NB_BUT_DOM", "NB_BUT_EXT"]].copy()
    dom.columns = ["POULE", "ID_EQUIPE", "NOM_EQUIPE", "BUTS_POUR", "BUTS_CONTRE"]
    dom["POINTS"] = dom.apply(lambda r: 3 if r.BUTS_POUR > r.BUTS_CONTRE else 1 if r.BUTS_POUR == r.BUTS_CONTRE else 0, axis=1)

    ext = matchs_complets[["POULE", "ID_EQUIPE_EXT", "EQUIPE_EXT", "NB_BUT_EXT", "NB_BUT_DOM"]].copy()
    ext.columns = ["POULE", "ID_EQUIPE", "NOM_EQUIPE", "BUTS_POUR", "BUTS_CONTRE"]
    ext["POINTS"] = ext.apply(lambda r: 3 if r.BUTS_POUR > r.BUTS_CONTRE else 1 if r.BUTS_POUR == r.BUTS_CONTRE else 0, axis=1)

    full = pd.concat([dom, ext])

    classement_df = full.groupby(["POULE", "ID_EQUIPE", "NOM_EQUIPE"]).agg(
        MJ=("POINTS", "count"),
        G=("POINTS", lambda x: (x == 3).sum()),
        N=("POINTS", lambda x: (x == 1).sum()),
        P=("POINTS", lambda x: (x == 0).sum()),
        BP=("BUTS_POUR", "sum"),
        BC=("BUTS_CONTRE", "sum"),
        POINTS=("POINTS", "sum")
    ).reset_index()

    classement_df["DIFF"] = classement_df["BP"] - classement_df["BC"]

    classement_df = appliquer_penalites(classement_df, date_limite)

    if type_classement == "PARTICULIERE":
        matchs_termine = get_matchs_termine(id_championnat, date_limite)
        classement_df, mini_classements = appliquer_diff_particuliere(classement_df, matchs_termine, selected_poule)
    else:
        mini_classements = {}

    classement_df = trier_et_numeroter(classement_df, type_classement)

    if selected_poule != "Toutes les poules":
        classement_df = classement_df[classement_df["POULE"] == selected_poule]

    return classement_df, mini_classements


def calculer_difficulte_calendrier(df_classement, df_matchs):
    """
    Calcule la difficulté moyenne du calendrier à venir pour chaque équipe,
    en se basant sur le classement actuel de leurs adversaires restants.
    """
    classement_dict = df_classement.set_index("ID_EQUIPE")["CLASSEMENT"].to_dict()
    confrontations = []

    for _, row in df_matchs.iterrows():
        id_dom = row["ID_EQUIPE_DOM"]
        id_ext = row["ID_EQUIPE_EXT"]

        if id_ext in classement_dict:
            confrontations.append((id_dom, classement_dict[id_ext]))
        if id_dom in classement_dict:
            confrontations.append((id_ext, classement_dict[id_dom]))

    df_confrontations = pd.DataFrame(confrontations, columns=["ID_EQUIPE", "CLASSEMENT_ADVERSAIRE"])

    df_difficulte = (
        df_confrontations
        .groupby("ID_EQUIPE")["CLASSEMENT_ADVERSAIRE"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"CLASSEMENT_ADVERSAIRE": "DIF_CAL"})
    )

    df_final = df_classement.merge(df_difficulte, on="ID_EQUIPE", how="left")
    df_final["DIF_CAL"] = df_final["DIF_CAL"].fillna(0.0)

    return df_final

import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- Connexion au Google Sheet ---
def connect_to_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key("1ODXBmpefw-wrCaUBmeQ1kkc2Lk2QQwWE2oYN5dobVek").worksheet("INSCRIPTIONS")
    return sheet

# --- Enregistrement de l'inscription ---
def enregistrer_inscription(email, prenom, nom, societe_club, newsletter, source):
    sheet = connect_to_google_sheet()
    
    # Lire tous les emails déjà présents (on saute la première ligne = en-têtes)
    existing_emails = [row[0] for row in sheet.get_all_values()[1:] if row]

    # Vérifier si l’email est déjà inscrit
    if email in existing_emails:
        st.warning("⚠️ Cet email est déjà inscrit.")
        return

    # Ajouter la nouvelle ligne
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [email, prenom, nom, societe_club, newsletter, source, now, "OK"]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    st.success("✅ Inscription enregistrée dans Google Sheet.")

# --- FONCTION DE RÉCUPÉRATION DES DONNÉES POUR RAPPORT CLUBS
def get_rapport_clubs(saison=None):
    condition_saison = f"WHERE ES.SAISON = {saison}" if saison else ""
    
    query = f"""
        WITH CHAMPIONNATS_RECENTS AS (
            SELECT * EXCEPT(row_num) FROM (
                SELECT 
                    ID_EQUIPE,
                    NOM_CHAMPIONNAT,
                    ROW_NUMBER() OVER (PARTITION BY ID_EQUIPE ORDER BY DATE DESC) AS row_num
                FROM (
                    SELECT 
                        M.ID_EQUIPE_DOM AS ID_EQUIPE,
                        CH.NOM_CHAMPIONNAT,
                        M.DATE
                    FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025` M
                    JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT` CH ON M.ID_CHAMPIONNAT = CH.ID_CHAMPIONNAT
                    
                    UNION ALL
                    
                    SELECT 
                        M.ID_EQUIPE_EXT AS ID_EQUIPE,
                        CH.NOM_CHAMPIONNAT,
                        M.DATE
                    FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025` M
                    JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT` CH ON M.ID_CHAMPIONNAT = CH.ID_CHAMPIONNAT
                )
            )
            WHERE row_num = 1
        )

        SELECT 
            ES.SAISON,
            EQ.ID_EQUIPE,
            EQ.NOM AS NOM_EQUIPE,
            EQ.CATEGORIE,
            EQ.NIVEAU,
            CL.ID_CLUB,
            CL.NOM_CLUB,
            DIST.NOM_DISTRICT,
            LIG.NOM_LIGUE,
            LIG.SHORT_LIGUE,
            CL.CENTRE,
            CL.TOP_400,
            ES.POULE,
            ES.STATUT_DEBUT,
            ES.STATUT_FIN,
            CR.NOM_CHAMPIONNAT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_EQUIPE_STATUT` ES
        JOIN `datafoot-448514.DATAFOOT.DATAFOOT_EQUIPE` EQ ON ES.ID_EQUIPE = EQ.ID_EQUIPE
        JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CLUB` CL ON EQ.ID_CLUB = CL.ID_CLUB
        JOIN `datafoot-448514.DATAFOOT.DATAFOOT_DISTRICT` DIST ON CL.ID_DISTRICT = DIST.ID_DISTRICT
        JOIN `datafoot-448514.DATAFOOT.DATAFOOT_LIGUE` LIG ON CL.ID_LIGUE = LIG.ID_LIGUE
        LEFT JOIN CHAMPIONNATS_RECENTS CR ON ES.ID_EQUIPE = CR.ID_EQUIPE
        {condition_saison}
        ORDER BY LIG.NOM_LIGUE, CL.NOM_CLUB, EQ.CATEGORIE
    """
    
    return client.query(query).to_dataframe()



def get_classement_filtres(saison, categorie, id_championnat=None, date_limite=None, journee_min=None, journee_max=None):
    import pandas as pd

    # --- Chargement des matchs filtrés
    if journee_min is not None and journee_max is not None:
        query = f"""
            SELECT *
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE STATUT = 'TERMINE'
              AND JOURNEE BETWEEN {journee_min} AND {journee_max}
        """
    elif date_limite is not None:
        query = f"""
            SELECT *
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE STATUT = 'TERMINE'
              AND DATE <= DATE('{date_limite}')
        """
    else:
        st.warning("❌ Vous devez spécifier une date ou une journée.")
        return pd.DataFrame()

    matchs = client.query(query).to_dataframe()
    if matchs.empty:
        return pd.DataFrame()

    # --- Création des lignes par équipe
    matchs_equipes = pd.concat([
        matchs.assign(
            ID_EQUIPE=matchs["ID_EQUIPE_DOM"],
            BUTS_POUR=matchs["NB_BUT_DOM"],
            BUTS_CONTRE=matchs["NB_BUT_EXT"],
            POINTS=matchs.apply(lambda row: 3 if row["NB_BUT_DOM"] > row["NB_BUT_EXT"] else (1 if row["NB_BUT_DOM"] == row["NB_BUT_EXT"] else 0), axis=1)
        ),
        matchs.assign(
            ID_EQUIPE=matchs["ID_EQUIPE_EXT"],
            BUTS_POUR=matchs["NB_BUT_EXT"],
            BUTS_CONTRE=matchs["NB_BUT_DOM"],
            POINTS=matchs.apply(lambda row: 3 if row["NB_BUT_EXT"] > row["NB_BUT_DOM"] else (1 if row["NB_BUT_EXT"] == row["NB_BUT_DOM"] else 0), axis=1)
        )
    ])

    stats = matchs_equipes.groupby("ID_EQUIPE").agg(
        MJ=('ID_EQUIPE', 'count'),
        POINTS=('POINTS', 'sum'),
        BP=('BUTS_POUR', 'sum'),
        BC=('BUTS_CONTRE', 'sum')
    ).reset_index()

    # --- Requête pour récupérer les infos clubs / poules / championnats
    query_infos = f"""
        SELECT * EXCEPT(row_num) FROM (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY ID_EQUIPE ORDER BY DATE DESC) AS row_num
            FROM (
                SELECT 
                    M.ID_EQUIPE_DOM AS ID_EQUIPE,
                    EQ_DOM.NOM AS NOM_EQUIPE,
                    EQ_DOM.NIVEAU,
                    CL.NOM_CLUB,
                    M.ID_CHAMPIONNAT,
                    M.POULE,
                    CH.NOM_CHAMPIONNAT,
                    M.DATE
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025` M
                JOIN `datafoot-448514.DATAFOOT.DATAFOOT_EQUIPE` EQ_DOM ON M.ID_EQUIPE_DOM = EQ_DOM.ID_EQUIPE
                JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CLUB` CL ON EQ_DOM.ID_CLUB = CL.ID_CLUB
                JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT` CH ON M.ID_CHAMPIONNAT = CH.ID_CHAMPIONNAT
                WHERE EQ_DOM.CATEGORIE = '{categorie}'

                UNION ALL

                SELECT 
                    M.ID_EQUIPE_EXT AS ID_EQUIPE,
                    EQ_EXT.NOM AS NOM_EQUIPE,
                    EQ_EXT.NIVEAU,
                    CL.NOM_CLUB,
                    M.ID_CHAMPIONNAT,
                    M.POULE,
                    CH.NOM_CHAMPIONNAT,
                    M.DATE
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025` M
                JOIN `datafoot-448514.DATAFOOT.DATAFOOT_EQUIPE` EQ_EXT ON M.ID_EQUIPE_EXT = EQ_EXT.ID_EQUIPE
                JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CLUB` CL ON EQ_EXT.ID_CLUB = CL.ID_CLUB
                JOIN `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT` CH ON M.ID_CHAMPIONNAT = CH.ID_CHAMPIONNAT
                WHERE EQ_EXT.CATEGORIE = '{categorie}'
            )
        ) WHERE row_num = 1
    """
    infos = client.query(query_infos).to_dataframe()

    # --- Fusion
    df = stats.merge(infos, on="ID_EQUIPE", how="left")

    # --- Filtrage sur le championnat s’il est précisé
    if id_championnat:
        df = df[df["ID_CHAMPIONNAT"].isin(id_championnat)].copy()

    # --- Ajout des STATUT_DEBUT et STATUT_FIN
    query_statut = f"""
        SELECT ID_EQUIPE, STATUT_DEBUT, STATUT_FIN
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_EQUIPE_STATUT`
        WHERE SAISON = {saison}
    """
    statut_df = client.query(query_statut).to_dataframe()
    df = df.merge(statut_df, on="ID_EQUIPE", how="left")

    # --- Application des pénalités (si date)
    if date_limite:
        df = appliquer_penalites(df, date_limite)

    # --- Sécurité
    df = df[df["POINTS"].notna()]
    df = df[df["POULE"].notna()].copy()

    # --- Classement par championnat + poule
    df["DIFF"] = df["BP"] - df["BC"]
    df = df.sort_values(by=["ID_CHAMPIONNAT", "POULE", "POINTS", "DIFF", "BP"], ascending=[True, True, False, False, False]).reset_index(drop=True)
    df["CLASSEMENT"] = df.groupby(["ID_CHAMPIONNAT", "POULE"]).cumcount() + 1
    df["CLASSEMENT"] = df["CLASSEMENT"].astype(int)

    # --- Moyenne
    df["MOY"] = (df["POINTS"] / df["MJ"]).round(2)

    colonnes = ["ID_EQUIPE", "NOM_CLUB", "NOM_EQUIPE", "NOM_CHAMPIONNAT", "POULE", "CLASSEMENT",
                "POINTS", "MOY", "MJ", "BP", "BC", "STATUT_DEBUT", "STATUT_FIN", "NIVEAU"]
    return df[colonnes]

