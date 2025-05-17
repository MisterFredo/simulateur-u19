import streamlit as st
import sys
import os

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simulateur_core import get_rapport_clubs

# --- CONFIG
st.set_page_config(page_title="RAPPORTS CLUBS - Datafoot", layout="wide")
st.markdown("## 📊 Rapports Clubs")

# --- FILTRE : SAISON
saisons_disponibles = ["2025", "2024", "2023"]
selected_saison = st.selectbox("Saison", ["Tous"] + saisons_disponibles, index=1)

# --- DONNÉES
df = get_rapport_clubs(saison=selected_saison if selected_saison != "Tous" else None)

# --- OPTIONS DYNAMIQUES
ligues_disponibles = sorted(df["NOM_LIGUE"].dropna().unique())
districts_disponibles = sorted(df["NOM_DISTRICT"].dropna().unique())
categories_disponibles = ["Tous"] + sorted(df["CATEGORIE"].dropna().unique())
niveaux_disponibles = ["Tous"] + sorted(df["NIVEAU"].dropna().unique())
statuts_disponibles = ["Tous"] + sorted(df["STATUT"].dropna().unique())
clubs_disponibles = sorted(df["NOM_CLUB"].dropna().unique())
championnats_disponibles = ["Tous"] + sorted(df["NOM_CHAMPIONNAT"].dropna().unique())

# --- FILTRES
col1, col2, col3 = st.columns(3)

with col1:
    selected_ligue = st.selectbox("Ligue", ["Toutes"] + ligues_disponibles)
    selected_district = st.selectbox("District", ["Tous"] + districts_disponibles)
    selected_championnat = st.selectbox("Championnat", championnats_disponibles)

with col2:
    selected_centre = st.selectbox("Centre de formation", ["Tous", "OUI", "NON"])
    selected_top400 = st.selectbox("Top 400 Europe", ["Tous", "OUI", "NON"])
    selected_clubs = st.multiselect("Clubs", clubs_disponibles, default=[])

with col3:
    selected_categorie = st.selectbox("Catégorie", categories_disponibles)
    selected_niveau = st.selectbox("Niveau", niveaux_disponibles)
    selected_statut = st.selectbox("Statut", statuts_disponibles)

# --- FILTRAGE
if selected_ligue != "Toutes":
    df = df[df["NOM_LIGUE"] == selected_ligue]

if selected_district != "Tous":
    df = df[df["NOM_DISTRICT"] == selected_district]

if selected_championnat != "Tous":
    df = df[df["NOM_CHAMPIONNAT"] == selected_championnat]

if selected_centre != "Tous":
    df = df[df["CENTRE"] == selected_centre]

if selected_top400 != "Tous":
    df = df[df["TOP_400"] == selected_top400]

if selected_clubs:
    df = df[df["NOM_CLUB"].isin(selected_clubs)]

if selected_categorie != "Tous":
    df = df[df["CATEGORIE"] == selected_categorie]

if selected_niveau != "Tous":
    df = df[df["NIVEAU"] == selected_niveau]

if selected_statut != "Tous":
    df = df[df["STATUT"] == selected_statut]

# --- SUPPRESSION DES COLONNES TECHNIQUES
df = df.drop(columns=["ID_CLUB", "ID_EQUIPE", "ID_CHAMPIONNAT", "NOM_LIGUE"], errors="ignore")

# --- AFFICHAGE FINAL (mobile-friendly)
colonnes_affichage = ["SAISON", "NOM_EQUIPE", "CATEGORIE", "NOM_CHAMPIONNAT"]
st.dataframe(df[colonnes_affichage], use_container_width=True, hide_index=True)

# --- EXPORT CSV
csv = df[colonnes_affichage].to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Télécharger le tableau (CSV)",
    data=csv,
    file_name="rapport_clubs.csv",
    mime="text/csv"
)
