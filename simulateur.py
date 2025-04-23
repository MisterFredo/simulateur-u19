import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration de la page
st.set_page_config(page_title="Classement - Datafoot", layout="wide")

# Connexion à BigQuery via secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

# Chargement des championnats
@st.cache_data(show_spinner=False)
def load_championnats():
    query = """
        SELECT ID_CHAMPIONNAT, NOM_CHAMPIONNAT, CATEGORIE, NIVEAU
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        ORDER BY CATEGORIE, NIVEAU, NOM_CHAMPIONNAT
    """
    return client.query(query).to_dataframe()

championnats_df = load_championnats()

# Filtres latéraux
st.sidebar.header("Filtres")
selected_categorie = st.sidebar.selectbox("Catégorie", sorted(championnats_df["CATEGORIE"].unique()))
selected_niveau = st.sidebar.selectbox(
    "Niveau", sorted(championnats_df[championnats_df["CATEGORIE"] == selected_categorie]["NIVEAU"].unique())
)
champ_options = championnats_df[
    (championnats_df["CATEGORIE"] == selected_categorie) &
    (championnats_df["NIVEAU"] == selected_niveau)
]
selected_nom = st.sidebar.selectbox("Championnat", champ_options["NOM_CHAMPIONNAT"])
champ_id = champ_options[champ_options["NOM_CHAMPIONNAT"] == selected_nom]["ID_CHAMPIONNAT"].values[0]

# Temporaire : pour charger les poules avant d'afficher la date
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

poules_temp = get_poules_temp(champ_id)
all_poules = sorted(poules_temp["POULE"].dropna().unique())
if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

# Date limite de simulation
date_limite = st.sidebar.date_input("Date de simulation", value=pd.to_datetime("2025-06-30"))

# Classement
@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
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

    # Debug
    print("REQUÊTE GÉNÉRÉE ==================")
    print(query)
    print("==================================")

    # ⬇️ Exécution + renommage
    classement_df = client.query(query).to_dataframe()
    classement_df = classement_df.rename(columns={"PTS": "POINTS"})
    return classement_df


def get_matchs_termine(champ_id, date_limite):
    query = f"""
        SELECT *
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE STATUT = 'TERMINE'
          AND ID_CHAMPIONNAT = {champ_id}
          AND DATE <= DATE('{date_limite}')
    """
    return client.query(query).to_dataframe()

# Type de classement
def get_type_classement(champ_id):
    query = f"""
        SELECT CLASSEMENT
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
        WHERE ID_CHAMPIONNAT = {champ_id}
        LIMIT 1
    """
    result = client.query(query).to_dataframe()
    return result.iloc[0]["CLASSEMENT"] if not result.empty else "GENERALE"

def appliquer_diff_particuliere(classement_df, matchs_df):
    st.write("🔍 Détection des égalités pour classement PARTICULIERE...")

    # 1. Regrouper les équipes à égalité de points par poule
    groupes = (
        classement_df
        .groupby(["POULE", "POINTS"])
        .filter(lambda x: len(x) > 1)  # garder seulement les égalités
        .groupby(["POULE", "POINTS"])
    )

    for (poule, pts), groupe in groupes:
        equipes_concernees = groupe["ID_EQUIPE"].tolist()

        # 2. Extraire les matchs entre ces équipes
        matchs_confrontations = matchs_df[
            (matchs_df["ID_EQUIPE_DOM"].isin(equipes_concernees)) &
            (matchs_df["ID_EQUIPE_EXT"].isin(equipes_concernees))
        ]

        st.write(f"📌 Poule {poule} — Égalité à {pts} pts entre {len(equipes_concernees)} équipes")
        st.dataframe(groupe[["NOM_EQUIPE", "POINTS", "DIFF"]])
        st.write("📄 Matchs concernés :")
        st.dataframe(matchs_confrontations[[
            "DATE", "EQUIPE_DOM", "EQUIPE_EXT", "NB_BUT_DOM", "NB_BUT_EXT"
        ]])

        # 3. Calcul du mini-classement
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

                # 🔁 Suppression préalable si la colonne existe
        if "RANG_CONFRONT" in classement_df.columns:
            classement_df.drop(columns=["RANG_CONFRONT"], inplace=True)

        # 🔁 Mise à jour dans le classement général
        classement_df = classement_df.merge(
            mini_df[["ID_EQUIPE", "RANG_CONFRONT"]],
            on="ID_EQUIPE",
            how="left"
        )

        # Remplissage des valeurs manquantes
        classement_df["RANG_CONFRONT"] = classement_df["RANG_CONFRONT"].fillna(999)

        # 👁️ Affichage pour contrôle
        st.write(f"🏅 Mini-classement pour égalité à {pts} pts")
        st.dataframe(mini_df)



        # 👁️ Inspection du classement mis à jour
        st.write("🧪 Vérification du classement après intégration de RANG_CONFRONT :")
        st.dataframe(classement_df[[
            "ID_EQUIPE", "NOM_EQUIPE", "POINTS", "RANG_CONFRONT"
        ]])
    
    return classement_df

def get_classement_particuliere(champ_id, date_limite):
    classement_base = get_classement_dynamique(champ_id, date_limite)
    matchs = get_matchs_termine(champ_id, date_limite)
    return appliquer_diff_particuliere(classement_base, matchs)

type_classement = get_type_classement(champ_id)
st.write("📌 Type de classement pour ce championnat :", type_classement)

# Chargement du classement adapté
if type_classement == "PARTICULIERE":
    classement_complet = get_classement_particuliere(champ_id, date_limite)
else:
    classement_complet = get_classement_dynamique(champ_id, date_limite)

# Chargement des pénalités valables à la date limite
penalites_actives = client.query(f"""
    SELECT ID_EQUIPE, POINTS
    FROM `datafoot-448514.DATAFOOT.DATAFOOT_PENALITE`
    WHERE DATE <= DATE('{date_limite}')
""").to_dataframe()

# Agrégation par équipe
penalites_agg = penalites_actives.groupby("ID_EQUIPE")["POINTS"].sum().reset_index()
penalites_agg.rename(columns={"POINTS": "PENALITES"}, inplace=True)

# Jointure avec le classement
classement_df = classement_complet.merge(penalites_agg, on="ID_EQUIPE", how="left")
classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0).astype(int)

# Mise à jour des points après pénalités
classement_df["PENALITES"] = classement_df["PENALITES"].fillna(0).astype(int)
classement_df["POINTS"] = classement_df["POINTS"] - classement_df["PENALITES"]

# 🧮 Recalcul du classement après pénalités et éventuelles égalités particulières
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

# Filtrage si une poule spécifique est sélectionnée
if selected_poule != "Toutes les poules":
    classement_df = classement_df[classement_df["POULE"] == selected_poule]

# Affichage
if classement_df.empty:
    st.warning("Aucun classement disponible pour ces critères.")
else:
    for poule in sorted(classement_df["POULE"].unique()):
        st.subheader(f"Poule {poule}")
        df = classement_df[classement_df["POULE"] == poule][[
            "CLASSEMENT", "NOM_EQUIPE", "POINTS", "PENALITES", "MJ", "G", "N", "P", "BP", "BC", "DIFF"
        ]].rename(columns={
            "MJ": "J."
        })
        st.dataframe(df, use_container_width=True)


st.caption("💡 Classement calculé à partir des matchs terminés uniquement, selon la date sélectionnée. Les pénalités sont déduites des points.")


# Les règles spécifiques sont désormais à adapter avec "classement_complet" pour avoir toutes les poules disponibles


# Cas particuliers (U19 / U17 / N2)
if selected_poule == "Toutes les poules":

    # U19 National - 11e
    if champ_id == 6 and not classement_df.empty:
        st.markdown("### 🚨 Classement spécial des 11èmes (règle U19 National)")
        df_11e = classement_df[classement_df["CLASSEMENT"] == 11]
        comparatif_11e = []

        @st.cache_data(show_spinner=False)
        def get_matchs_u19(champ_id, date_limite):
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
            """
            return client.query(query).to_dataframe()

        matchs_u19 = get_matchs_u19(champ_id, date_limite)

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
                    if m["NB_BUT_DOM"] > m["NB_BUT_EXT"]: pts += 3
                    elif m["NB_BUT_DOM"] == m["NB_BUT_EXT"]: pts += 1
                elif m["EQUIPE_EXT"] == equipe_11e:
                    if m["NB_BUT_EXT"] > m["NB_BUT_DOM"]: pts += 3
                    elif m["NB_BUT_EXT"] == m["NB_BUT_DOM"]: pts += 1

            comparatif_11e.append({"POULE": poule, "EQUIPE": equipe_11e, "PTS_CONFRONT_6_10": pts})

        df_11e_comp = pd.DataFrame(comparatif_11e).sort_values("PTS_CONFRONT_6_10")
        df_11e_comp["RANG"] = df_11e_comp["PTS_CONFRONT_6_10"].rank(method="min")
        st.dataframe(df_11e_comp, use_container_width=True)

    # U17 National - 2e
    if champ_id == 7 and not classement_df.empty:
        st.markdown("### 🥈 Comparatif des 2e (règle U17 National)")

        df_2e = classement_df[classement_df["CLASSEMENT"] == 2]
        comparatif_2e = []

        for _, row in df_2e.iterrows():
            poule = row["POULE"]
            equipe_2e = row["NOM_EQUIPE"]

            top_5 = classement_df[
                (classement_df["POULE"] == poule) &
                (classement_df["CLASSEMENT"].between(1, 5))
            ]["NOM_EQUIPE"].tolist()

            @st.cache_data(show_spinner=False)
            def get_matchs_poule(champ_id, poule):
                query = f"""
                    SELECT EQUIPE_DOM, EQUIPE_EXT, NB_BUT_DOM, NB_BUT_EXT
                    FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                    WHERE ID_CHAMPIONNAT = {champ_id}
                      AND POULE = '{poule}'
                      AND STATUT = 'TERMINE'
                """
                return client.query(query).to_dataframe()

            matchs_poule = get_matchs_poule(champ_id, poule)

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
        df_2e_comp["RANG"] = df_2e_comp["PTS_CONFRONT_TOP5"].rank(method="min", ascending=False)
        st.dataframe(df_2e_comp, use_container_width=True)

    # N2 - 13e
    if champ_id == 4 and not classement_df.empty:
        st.markdown("### 🚨 Comparatif des 13e (règle N2)")

        df_13e = classement_df[classement_df["CLASSEMENT"] == 13]
        comparatif_13e = []

        @st.cache_data(show_spinner=False)
        def get_matchs_n2(champ_id, date_limite):
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
            """
            return client.query(query).to_dataframe()

        matchs_n2 = get_matchs_n2(champ_id, date_limite)

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
        df_13e_comp["RANG"] = df_13e_comp["PTS_CONFRONT_8_12"].rank(method="min", ascending=False)
        st.dataframe(df_13e_comp, use_container_width=True)
    # N3 - 10e
    if champ_id == 5 and not classement_df.empty:
        st.markdown("### ⚠️ Comparatif des 10e (règle N3)")

        df_10e = classement_df[classement_df["CLASSEMENT"] == 10]
        comparatif_10e = []

        @st.cache_data(show_spinner=False)
        def get_matchs_n3(champ_id, date_limite):
            query = f"""
                SELECT *
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE STATUT = 'TERMINE'
                  AND ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
            """
            return client.query(query).to_dataframe()

        matchs_n3 = get_matchs_n3(champ_id, date_limite)

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
        df_10e_comp["RANG"] = df_10e_comp["PTS_CONFRONT_5_9"].rank(method="min", ascending=False)
        st.dataframe(df_10e_comp, use_container_width=True)



else:
    if champ_id in [4, 5, 6, 7]:
        st.info("🔒 Les règles spécifiques (U19, U17, N2, N3) ne sont disponibles que si toutes les poules sont affichées.")
