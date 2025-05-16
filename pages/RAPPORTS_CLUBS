import streamlit as st
import sys
import os

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulateur_core import get_rapport_clubs

# --- CONFIG STREAMLIT
st.set_page_config(page_title="RAPPORTS CLUBS - Datafoot", layout="wide")

# --- SIDEBAR : Navigation entre les pages
st.sidebar.markdown("## Navigation")
st.sidebar.page_link("HOME.py", label="Accueil")
st.sidebar.page_link("pages/ANALYSE_CHAMPIONNAT.py", label="Analyse Championnat")
st.sidebar.page_link("pages/RAPPORTS_CLUBS.py", label="Rapports Clubs")

# --- CORPS PRINCIPAL
st.markdown("## 📊 Rapports Clubs")

# --- FILTRE : SAISON
selected_saison = st.selectbox("Saison", options=["2025", "2024", "2023"], index=0)

# --- RÉCUPÉRATION DES DONNÉES
df_clubs = get_rapport_clubs(saison=selected_saison)

# --- AFFICHAGE TABLEAU
st.dataframe(df_clubs, use_container_width=True, hide_index=True)
