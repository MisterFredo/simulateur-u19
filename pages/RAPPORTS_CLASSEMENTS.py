import streamlit as st
import sys
import os

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
statuts_disponibles = sorted(df_ref["STATUT"].dropna().unique())
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
    selected_statuts = st.multiselect("Statuts", statuts_disponibles)

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

    # Récupération de l'ID_CHAMPIONNAT à partir du nom sélectionné
    id_championnat = df_ref[df_ref["NOM_CHAMPIONNAT"] == selected_championnats[0]]["ID_CHAMPIONNAT"].values[0] if selected_championnats else None

    # Appel à la fonction avec l'ID du championnat
    df = get_classement_filtres(
        saison=selected_saison,
        categorie=selected_categories[0] if selected_categories else "SENIOR",
        id_championnat=id_championnat,
        date_limite=str(date_limite) if date_limite else None,
        journee_min=journee_min,
        journee_max=journee_max
    )
    if selected_ligues:
        equipes_filtrees = df_ref[df_ref["NOM_LIGUE"].isin(selected_ligues)]["NOM_EQUIPE"].unique()
        df = df[df["NOM_EQUIPE"].isin(equipes_filtrees)]

    if selected_districts:
        equipes_filtrees = df_ref[df_ref["NOM_DISTRICT"].isin(selected_districts)]["NOM_EQUIPE"].unique()
        df = df[df["NOM_EQUIPE"].isin(equipes_filtrees)]

    if selected_championnats:
        df = df[df["NOM_CHAMPIONNAT"].isin(selected_championnats)]

    if selected_centre != "Tous":
        equipes_filtrees = df_ref[df_ref["CENTRE"] == selected_centre]["NOM_EQUIPE"].unique()
        df = df[df["NOM_EQUIPE"].isin(equipes_filtrees)]

    if selected_top400 != "Tous":
        equipes_filtrees = df_ref[df_ref["TOP_400"] == selected_top400]["NOM_EQUIPE"].unique()
        df = df[df["NOM_EQUIPE"].isin(equipes_filtrees)]

    if selected_clubs:
        df = df[df["NOM_CLUB"].isin(selected_clubs)]

    if selected_niveaux:
        equipes_filtrees = df_ref[df_ref["NIVEAU"].isin(selected_niveaux)]["NOM_EQUIPE"].unique()
        df = df[df["NOM_EQUIPE"].isin(equipes_filtrees)]

    if selected_statuts:
        equipes_filtrees = df_ref[df_ref["STATUT"].isin(selected_statuts)]["NOM_EQUIPE"].unique()
        df = df[df["NOM_EQUIPE"].isin(equipes_filtrees)]

    if len(df) > 500:
        st.warning(f"⚠️ Affichage limité à 500 lignes sur {len(df)} résultats.")
        df = df.head(500)

    if mobile_mode:
        colonnes_affichage = ["NOM_CLUB", "NOM_EQUIPE", "NOM_CHAMPIONNAT", "CLASSEMENT"]
        st.dataframe(df[colonnes_affichage], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    # --- EXPORT (commenté)
    # csv = df.to_csv(index=False).encode("utf-8")
    # st.download_button(
    #     label="📥 Télécharger le tableau (CSV)",
    #     data=csv,
    #     file_name="classement_performance.csv",
    #     mime="text/csv"
    # )
