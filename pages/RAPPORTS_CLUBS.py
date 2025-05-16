import streamlit as st
import sys
import os

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simulateur_core import get_rapport_clubs

# --- CONFIG
st.set_page_config(page_title="RAPPORTS CLUBS - Datafoot", layout="wide")

# --- TITRE
st.markdown("## 📊 Rapports Clubs")

# --- FILTRES
col1, col2, col3 = st.columns(3)

with col1:
    selected_saison = st.selectbox("Saison", ["2025", "2024", "2023"], index=0)
    selected_ligue = st.selectbox("Ligue", ["Toutes", "HAUTS DE FRANCE", "ILE DE FRANCE", "AUVERGNE-RHÔNE-ALPES"])

with col2:
    selected_district = st.selectbox("District", ["Tous", "Nord", "Seine-Saint-Denis", "Loire", "Autres..."])
    selected_centre = st.selectbox("Centre de formation", ["Tous", "OUI", "NON"])
    selected_top400 = st.selectbox("Top 400 Europe", ["Tous", "OUI", "NON"])

with col3:
    selected_categorie = st.selectbox("Catégorie", ["SENIOR", "U19", "U18", "U17", "U16", "U15"])
    selected_niveau = st.selectbox("Niveau", ["PREMIERE", "RESERVE", "THIRD"])
    selected_statut = st.selectbox("Statut dans le championnat", ["Tous", "PROMUE", "MAINTENUE", "RELEGUEE"])

# --- DONNÉES
df = get_rapport_clubs(saison=selected_saison)

# --- FILTRAGE
if selected_ligue != "Toutes":
    df = df[df["LIGUE"] == selected_ligue]

if selected_district != "Tous":
    df = df[df["DISTRICT"] == selected_district]

if selected_centre != "Tous":
    df = df[df["CENTRE"] == selected_centre]

if selected_top400 != "Tous":
    df = df[df["TOP_400"] == selected_top400]

if selected_categorie:
    df = df[df["CATEGORIE"] == selected_categorie]

if selected_niveau:
    df = df[df["NIVEAU"] == selected_niveau]

if selected_statut != "Tous":
    df = df[df["STATUT"] == selected_statut]

# --- AFFICHAGE
st.dataframe(df, use_container_width=True, hide_index=True)
