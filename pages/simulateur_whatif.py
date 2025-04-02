import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuration
st.set_page_config(page_title="Simulation What If", layout="wide")

# Connexion BigQuery
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

# Filtres
st.sidebar.header("Filtres simulation")
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

# Sélecteur de poule
@st.cache_data(show_spinner=False)
def get_poules(champ_id):
    query = f"""
        SELECT DISTINCT POULE
        FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
        WHERE ID_CHAMPIONNAT = {champ_id} AND POULE IS NOT NULL
        ORDER BY POULE
    """
    return client.query(query).to_dataframe()

poules_df = get_poules(champ_id)
all_poules = sorted(poules_df["POULE"].dropna().unique())
if len(all_poules) > 1:
    selected_poule = st.sidebar.selectbox("Poule", ["Toutes les poules"] + all_poules)
else:
    selected_poule = all_poules[0] if all_poules else "Toutes les poules"

date_limite = st.sidebar.date_input("Date max à prendre en compte", value=pd.to_datetime("2025-03-31"))

# Affichage des matchs modifiables
st.title("🧪 Simulation What If")

filtrer_non_joues = st.checkbox("Afficher uniquement les matchs non joués", value=True)

@st.cache_data(show_spinner=False)
def get_matchs_modifiables(champ_id, date_limite, non_joues_only):
    condition = "AND STATUT IS NULL" if non_joues_only else ""
    query = f"""
        SELECT 
            ID_MATCH,
            JOURNEE,
            POULE,
            DATE,
            EQUIPE_DOM,
            NB_BUT_DOM,
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

matchs_simulables = get_matchs_modifiables(champ_id, date_limite, filtrer_non_joues)
if selected_poule != "Toutes les poules":
    matchs_simulables = matchs_simulables[matchs_simulables["POULE"] == selected_poule]

if matchs_simulables.empty:
    st.info("Aucun match à afficher pour cette configuration.")
else:
    st.markdown("### Matchs simulables")
    df_simulation = matchs_simulables.copy()
    edited_df = st.data_editor(
        df_simulation[["ID_MATCH", "JOURNEE", "POULE", "DATE", "EQUIPE_DOM", "NB_BUT_DOM", "EQUIPE_EXT", "NB_BUT_EXT", "STATUT"]],
        num_rows="dynamic",
        use_container_width=True,
        key="simulation_scores"
    )
    if st.button("🔁 Recalculer le classement avec ces scores simulés"):
        st.session_state["simulated_scores"] = edited_df
        st.success("Scores pris en compte. On peut maintenant recalculer le classement.")

# Calcul du classement simulé
if "simulated_scores" in st.session_state:
    df_sim = st.session_state["simulated_scores"]
    df_valid = df_sim.dropna(subset=["NB_BUT_DOM", "NB_BUT_EXT"])

    if df_valid.empty:
        st.warning("Aucun score simulé n’a été saisi.")
    else:
        st.markdown("### 📊 Classement simulé (avec scores simulés + résultats réels)")

        @st.cache_data(show_spinner=False)
        def get_matchs_termines(champ_id, date_limite):
            query = f"""
                SELECT ID_MATCH, JOURNEE, POULE, DATE, EQUIPE_DOM, NB_BUT_DOM, EQUIPE_EXT, NB_BUT_EXT, STATUT
                FROM `datafoot-448514.DATAFOOT.DATAFOOT_MATCH_2025`
                WHERE ID_CHAMPIONNAT = {champ_id}
                  AND DATE <= DATE('{date_limite}')
                  AND STATUT = 'TERMINE'
            """
            return client.query(query).to_dataframe()

        matchs_termines = get_matchs_termines(champ_id, date_limite)

        df_simules = df_valid.set_index("ID_MATCH")
        matchs_termines = matchs_termines.set_index("ID_MATCH")
        matchs_reels_sans_doublon = matchs_termines[~matchs_termines.index.isin(df_simules.index)]
        matchs_complets = pd.concat([matchs_reels_sans_doublon, df_simules]).reset_index()

        dom = matchs_complets.rename(columns={"EQUIPE_DOM": "NOM_EQUIPE", "NB_BUT_DOM": "BUTS_POUR", "NB_BUT_EXT": "BUTS_CONTRE"})
        dom["POINTS"] = dom.apply(lambda r: 3 if r.BUTS_POUR > r.BUTS_CONTRE else (1 if r.BUTS_POUR == r.BUTS_CONTRE else 0), axis=1)

        ext = matchs_complets.rename(columns={"EQUIPE_EXT": "NOM_EQUIPE", "NB_BUT_EXT": "BUTS_POUR", "NB_BUT_DOM": "BUTS_CONTRE"})
        ext["POINTS"] = ext.apply(lambda r: 3 if r.BUTS_POUR > r.BUTS_CONTRE else (1 if r.BUTS_POUR == r.BUTS_CONTRE else 0), axis=1)

        full = pd.concat([dom, ext])[["POULE", "NOM_EQUIPE", "BUTS_POUR", "BUTS_CONTRE", "POINTS"]]
        classement = full.groupby(["POULE", "NOM_EQUIPE"]).agg(
            MJ=("POINTS", "count"),
            G=("POINTS", lambda x: (x == 3).sum()),
            N=("POINTS", lambda x: (x == 1).sum()),
            P=("POINTS", lambda x: (x == 0).sum()),
            BP=("BUTS_POUR", "sum"),
            BC=("BUTS_CONTRE", "sum"),
            PTS=("POINTS", "sum")
        ).reset_index()

        classement["DIFF"] = classement["BP"] - classement["BC"]
        classement = classement.sort_values(by=["POULE", "PTS", "DIFF", "BP"], ascending=[True, False, False, False])
        classement["CLASSEMENT"] = classement.groupby("POULE").cumcount() + 1

        if selected_poule != "Toutes les poules":
            classement = classement[classement["POULE"] == selected_poule]

        for poule in sorted(classement["POULE"].unique()):
            st.subheader(f"Poule {poule}")
            df = classement[classement["POULE"] == poule][[
                "CLASSEMENT", "NOM_EQUIPE", "PTS", "BP", "BC", "DIFF", "MJ"
            ]].rename(columns={
                "PTS": "POINTS", "BP": "BUTS_POUR", "BC": "BUTS_CONTRE", "MJ": "MATCHS_JOUES"
            })
            st.dataframe(df, use_container_width=True)
