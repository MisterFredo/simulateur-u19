import streamlit as st
import sys
import os
from google.cloud import bigquery

# --- ACCÈS RÉSERVÉ À FREDERIC ---
if st.session_state.get("user_email") != "mister.fredo@gmail.com":
    st.warning("🚫 Accès réservé à l’administrateur.")
    st.stop()

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simulateur_core import get_classement_filtres, get_rapport_clubs

# --- CONFIG
st.set_page_config(page_title="RAPPORTS CLASSEMENTS - Datafoot", layout="wide")
st.markdown("## 🏆 Classements par performance")

# --- CHECKBOX MOBILE
mobile_mode = st.checkbox("📱 Mode Mobile Friendly", value=False)

# --- FILTRE SAISON / CATÉGORIE
saisons_disponibles = ["2025", "2024", "2023"]
selected_saison = st.selectbox("Saison", saisons_disponibles)

# --- DONNÉES POUR OPTIONS
df_ref = get_rapport_clubs(saison=selected_saison)

ligues_disponibles = sorted(df_ref["NOM_LIGUE"].dropna().unique())
districts_disponibles = sorted(df_ref["NOM_DISTRICT"].dropna().unique())
categories_disponibles = sorted(df_ref["CATEGORIE"].dropna().unique())
niveaux_disponibles = sorted(df_ref["NIVEAU"].dropna().unique())
statuts_debut_disponibles = sorted(df_ref["STATUT_DEBUT"].dropna().unique())
statuts_fin_disponibles = sorted(df_ref["STATUT_FIN"].dropna().unique())
clubs_disponibles = sorted(df_ref["NOM_CLUB"].dropna().unique())
championnats_disponibles = sorted(df_ref["NOM_CHAMPIONNAT"].dropna().unique())

# --- MULTI-FILTRES
col1, col2, col3 = st.columns(3)

with col1:
    selected_ligues = st.multiselect("Ligues", ligues_disponibles)
    selected_districts = st.multiselect("Districts", districts_disponibles)
    selected_championnats = st.multiselect("Championnats", championnats_disponibles)

with col2:
    selected_centre = st.selectbox("Centre de formation", ["Tous", "OUI", "NON"])
    selected_top400 = st.selectbox("Top 400 Europe", ["Tous", "OUI", "NON"])
    selected_clubs = st.multiselect("Clubs", clubs_disponibles)

with col3:
    selected_categories = st.multiselect("Catégories", categories_disponibles)
    selected_niveaux = st.multiselect("Niveaux", niveaux_disponibles)
    selected_statuts_debut = st.multiselect("Statuts de début", statuts_debut_disponibles)
    selected_statuts_fin = st.multiselect("Statuts de fin", statuts_fin_disponibles)

# --- MODE DE CLASSEMENT
mode = st.radio("Mode de classement", ["Par date (pénalités incluses)", "Par journées (sans pénalités)"])

if mode == "Par date (pénalités incluses)":
    date_limite = st.date_input("Date limite")
    journee_min = None
    journee_max = None
else:
    colj1, colj2 = st.columns(2)
    with colj1:
        journee_min = st.number_input("Journée min", min_value=1, max_value=30, step=1)
    with colj2:
        journee_max = st.number_input("Journée max", min_value=1, max_value=30, step=1)
    date_limite = None

# --- AFFICHAGE DU CLASSEMENT
if st.button("Afficher le classement"):

    # Mapping dynamique NOM_CHAMPIONNAT -> ID_CHAMPIONNAT
    if selected_championnats:
        query_champ = """
            SELECT ID_CHAMPIONNAT
            FROM `datafoot-448514.DATAFOOT.DATAFOOT_CHAMPIONNAT`
            WHERE NOM_CHAMPIONNAT IN UNNEST(@selected_championnats)
        """
        client = bigquery.Client()
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("selected_championnats", "STRING", selected_championnats)
            ]
        )
        champ_df = client.query(query_champ, job_config=job_config).to_dataframe()
        id_championnat = champ_df["ID_CHAMPIONNAT"].unique().tolist()
    else:
        id_championnat = None

    # Appel à la fonction avec l'ID du championnat
    df = get_classement_filtres(
        saison=selected_saison,
        categorie=selected_categories[0] if selected_categories else "SENIOR",
        id_championnat=id_championnat,
        date_limite=str(date_limite) if date_limite else None,
        journee_min=journee_min,
        journee_max=journee_max
    )

    # --- FILTRES POST-CALCUL
    if selected_ligues:
        equipes_filtrees = df_ref[df_ref["NOM_LIGUE"].isin(selected_ligues)]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_districts:
        equipes_filtrees = df_ref[df_ref["NOM_DISTRICT"].isin(selected_districts)]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_centre != "Tous":
        equipes_filtrees = df_ref[df_ref["CENTRE"] == selected_centre]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_top400 != "Tous":
        equipes_filtrees = df_ref[df_ref["TOP_400"] == selected_top400]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_clubs:
        equipes_filtrees = df_ref[df_ref["NOM_CLUB"].isin(selected_clubs)]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_niveaux:
        equipes_filtrees = df_ref[df_ref["NIVEAU"].isin(selected_niveaux)]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_statuts_debut:
        equipes_filtrees = df_ref[df_ref["STATUT_DEBUT"].isin(selected_statuts_debut)]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    if selected_statuts_fin:
        equipes_filtrees = df_ref[df_ref["STATUT_FIN"].isin(selected_statuts_fin)]["ID_EQUIPE"].unique()
        df = df[df["ID_EQUIPE"].isin(equipes_filtrees)]

    # --- LIMITATION À 500 LIGNES
    if len(df) > 500:
        st.warning(f"⚠️ Affichage limité à 500 lignes sur {len(df)} résultats.")
        df = df.head(500)

    # --- AFFICHAGE FINAL
    if mobile_mode:
        colonnes_affichage = ["NOM_CLUB", "NOM_EQUIPE", "NOM_CHAMPIONNAT", "CLASSEMENT"]
        st.dataframe(df[colonnes_affichage], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    # --- EXPORT CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Télécharger le tableau (CSV)",
        data=csv,
        file_name="classement_performance.csv",
        mime="text/csv"
    )

