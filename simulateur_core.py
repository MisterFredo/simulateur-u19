import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

def get_type_classement(champ_id):
    query = f"""
        SELECT CLASSEMENT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        WHERE ID_CHAMPIONNAT = {champ_id}
        LIMIT 1
    """
    result = client.query(query).to_dataframe()
    return result.iloc[0]["CLASSEMENT"] if not result.empty else "GENERALE"

def get_classement_dynamique(champ_id, date_limite):
    query = f"""
        WITH matchs_termine AS (
          SELECT *
          FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
          WHERE STATUT = 'TERMINE'
            AND ID_CHAMPIONNAT = {champ_id}
            AND DATE <= DATE('{date_limite}')
        ),
        match_equipes AS (
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE_DOM AS ID_EQUIPE, EQUIPE_DOM AS NOM_EQUIPE,
                 NB_BUT_DOM AS BUTS_POUR, NB_BUT_EXT AS BUTS_CONTRE,
                 CASE WHEN NB_BUT_DOM > NB_BUT_EXT THEN 3 WHEN NB_BUT_DOM = NB_BUT_EXT THEN 1 ELSE 0 END AS POINTS
          FROM matchs_termine
          UNION ALL
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE_EXT, EQUIPE_EXT, NB_BUT_EXT, NB_BUT_DOM,
                 CASE WHEN NB_BUT_EXT > NB_BUT_DOM THEN 3 WHEN NB_BUT_EXT = NB_BUT_DOM THEN 1 ELSE 0 END
          FROM matchs_termine
        ),
        classement AS (
          SELECT ID_CHAMPIONNAT, POULE, ID_EQUIPE, NOM_EQUIPE,
                 COUNT(*) AS MJ,
                 SUM(CASE WHEN POINTS = 3 THEN 1 ELSE 0 END) AS G,
                 SUM(CASE WHEN POINTS = 1 THEN 1 ELSE 0 END) AS N,
                 SUM(CASE WHEN POINTS = 0 THEN 1 ELSE 0 END) AS P,
                 SUM(BUTS_POUR) AS BP,
                 SUM(BUTS_CONTRE) AS BC,
                 SUM(BUTS_POUR - BUTS_CONTRE) AS DIFF,
                 SUM(POINTS) AS PTS
          FROM match_equipes
          GROUP BY ID_CHAMPIONNAT, POULE, ID_EQUIPE, NOM_EQUIPE
        )
        SELECT *, RANK() OVER (PARTITION BY ID_CHAMPIONNAT, POULE ORDER BY PTS DESC, DIFF DESC, BP DESC) AS CLASSEMENT
        FROM classement
        ORDER BY POULE, CLASSEMENT
    """
    df = client.query(query).to_dataframe()
    return df.rename(columns={"PTS": "POINTS"})

def get_matchs_termine(champ_id, date_limite):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
    """
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

@st.cache_data(show_spinner=False)
def get_poules_temp(champ_id):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()

@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

def appliquer_penalites(classement_df, date_limite):
    penalites_actives = client.query(f"""
        SELECT ID_EQUIPE, POINTS
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_PENALITE`
        WHERE DATE <= DATE('{date_limite}')
    """).to_dataframe()

    penalites_agg = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
    penalites_agg.rename(columns={"POINTS": "PENALITES"}, inplace=True)

    # Fusion avec les points, sans créer de doublon de colonnes
    classement_df = classement_df.merge(penalites_agg, on="ID_EQUIPE", how="left")

    # Sécurisation de la colonne
    classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0).astype(int)

    # Application des pénalités sur les POINTS
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

def classement_special_u19(classement_df, champ_id, date_limite):
    if champ_id != 6 or classement_df.empty:
        return None

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
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

def classement_special_u17(classement_df, champ_id, client):
    if champ_id != 7 or classement_df.empty:
        return None

    df_2e = classement_df[classement_df["CLASSEMENT"] == 2]
    comparatif_2e = []

    for _, row in df_2e.iterrows():
        poule = row["POULE"]
        equipe_2e = row["NOM_EQUIPE"]

        top_5 = classement_df[
            (classement_df["POULE"] == poule) &
            (classement_df["CLASSEMENT"].between(1, 5))
        ]["NOM_EQUIPE"].tolist()

        query = f"""
            SELECT EQUIPE_DOM, EQUIPE_EXT, NB_BUT_DOM, NB_BUT_EXT
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
            WHERE ID_CHAMPIONNAT = {champ_id}
              AND POULE = '{poule}'
              AND STATUT = 'TERMINE'
        """
        matchs_poule = client.query(query).to_dataframe()

        confrontations = matchs_poule[
            ((matchs_poule["EQUIPE_DOM"] == equipe_2e) & (matchs_poule["EQUIPE_EXT"].isin(top_5))) |
            ((matchs_poule["EQUIPE_EXT"] == equipe_2e) & (matchs_poule["EQUIPE_DOM"].isin(top_5)))
        ]

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

    df_2e_comp = pd.DataFrame(comparatif_2e).sort_values("PTS_CONFRONT_TOP5", ascending=False)
    df_2e_comp["RANG"] = df_2e_comp["PTS_CONFRONT_TOP5"].rank(method="min", ascending=False).astype(int)
    return df_2e_comp

def classement_special_n2(classement_df, champ_id, date_limite):
    if champ_id != 4 or classement_df.empty:
        return None

    df_13e = classement_df[classement_df["CLASSEMENT"] == 13]
    comparatif_13e = []

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
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

def classement_special_n3(classement_df, champ_id, date_limite):
    if champ_id != 5 or classement_df.empty:
        return None

    df_10e = classement_df[classement_df["CLASSEMENT"] == 10]
    comparatif_10e = []

    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
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

def get_matchs_modifiables(champ_id, date_limite, non_joues_only=True):
    condition = "AND STATUT IS NULL" if non_joues_only else ""
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
        WHERE ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
          {condition}
        ORDER BY DATE, JOURNEE
    """
    return client.query(query).to_dataframe()

def recalculer_classement_simule(matchs_simules, champ_id, date_limite, selected_poule, type_classement):
    # Récupération des matchs terminés à date, hors ceux qu'on va simuler
    matchs_historiques = get_matchs_termine(champ_id, date_limite)
    matchs_historiques = matchs_historiques[~matchs_historiques["ID_MATCH"].isin(matchs_simules["ID_MATCH"])]

    # Fusion avec les scores simulés
    matchs_complets = pd.concat([matchs_historiques, matchs_simules], ignore_index=True)

    # Construction du tableau complet
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

    # Application des pénalités
    classement_df = appliquer_penalites(classement_df, date_limite)

    # Application des égalités particulières si besoin
    if type_classement == "PARTICULIERE":
        matchs_termine = get_matchs_termine(champ_id, date_limite)
        classement_df, mini_classements = appliquer_diff_particuliere(classement_df, matchs_termine, selected_poule)
    else:
        mini_classements = {}

    # Tri final
    classement_df = trier_et_numeroter(classement_df, type_classement)

    # Filtrage par poule si sélectionnée
    if selected_poule != "Toutes les poules":
        classement_df = classement_df[classement_df["POULE"] == selected_poule]

    # DEBUG : Vérification des matchs avant et après concaténation
    st.write("🧪 Matchs simulés (transmis) :", matchs_simules[["ID_MATCH", "NB_BUT_DOM", "NB_BUT_EXT"]])
    st.write("🧪 Matchs historiques :", matchs_historiques[["ID_MATCH"]].head())
    st.write("🧪 Tous les matchs (concaténés) :", matchs_complets[["ID_MATCH", "NB_BUT_DOM", "NB_BUT_EXT"]].head())


    return classement_df, mini_classements

