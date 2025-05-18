import streamlit as st
import sys
import os

# --- ACCÈS RÉSERVÉ À FREDERIC ---
if st.session_state.get("user_email") != "mister.fredo@gmail.com":
    st.warning("🚫 Accès réservé à l’administrateur.")
    st.stop()

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simulateur_core import get_rapport_clubs

# --- CONFIG
st.set_page_config(page_title="RAPPORTS CLUBS - Datafoot", layout="wide")
st.markdown("## 📊 Rapports Clubs")

# --- CHECKBOX MOBILE
mobile_mode = st.checkbox("📱 Mode Mobile Friendly", value=False)

# --- FILTRE : SAISON
saisons_disponibles = ["2025", "2024", "2023"]
selected_saison = st.selectbox("Saison", ["Toutes"] + saisons_disponibles)

# --- DONNÉES
df = get_rapport_clubs(saison=selected_saison if selected_saison != "Toutes" else None)

# --- OPTIONS DYNAMIQUES
ligues_disponibles = sorted(df["NOM_LIGUE"].dropna().unique())
districts_disponibles = sorted(df["NOM_DISTRICT"].dropna().unique())
categories_disponibles = sorted(df["CATEGORIE"].dropna().unique())
niveaux_disponibles = sorted(df["NIVEAU"].dropna().unique())
statuts_disponibles = sorted(df["STATUT"].dropna().unique())
clubs_disponibles = sorted(df["NOM_CLUB"].dropna().unique())
championnats_disponibles = sorted(df["NOM_CHAMPIONNAT"].dropna().unique())

# --- FILTRES
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

# --- FILTRAGE MULTI
if selected_ligues:
    df = df[df["NOM_LIGUE"].isin(selected_ligues)]

if selected_districts:
    df = df[df["NOM_DISTRICT"].isin(selected_districts)]

if selected_championnats:
    df = df[df["NOM_CHAMPIONNAT"].isin(selected_championnats)]

if selected_centre != "Tous":
    df = df[df["CENTRE"] == selected_centre]

if selected_top400 != "Tous":
    df = df[df["TOP_400"] == selected_top400]

if selected_clubs:
    df = df[df["NOM_CLUB"].isin(selected_clubs)]

if selected_categories:
    df = df[df["CATEGORIE"].isin(selected_categories)]

if selected_niveaux:
    df = df[df["NIVEAU"].isin(selected_niveaux)]

if selected_statuts:
    df = df[df["STATUT"].isin(selected_statuts)]

# --- SUPPRESSION COLONNES TECHNIQUES
colonnes_a_supprimer = ["ID_CLUB", "ID_EQUIPE", "ID_CHAMPIONNAT", "NOM_LIGUE"]
df = df.drop(columns=[col for col in colonnes_a_supprimer if col in df.columns])

# --- LIMITATION AFFICHAGE
if len(df) > 500:
    st.warning(f"⚠️ Affichage limité à 500 lignes sur {len(df)} résultats.")
    df = df.head(500)

# --- AFFICHAGE
if mobile_mode:
    colonnes_affichage = ["SAISON", "NOM_EQUIPE", "CATEGORIE", "NOM_CHAMPIONNAT"]
    st.dataframe(df[colonnes_affichage], use_container_width=True, hide_index=True)
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- EXPORT (commenté)
# csv = df.to_csv(index=False).encode("utf-8")
# st.download_button(
#     label="📥 Télécharger le tableau (CSV)",
#     data=csv,
#     file_name="rapport_clubs.csv",
#     mime="text/csv"
# )

