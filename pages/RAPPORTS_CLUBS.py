import streamlit as st
import sys
import os

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulateur_core import get_rapport_clubs

# --- CONFIG STREAMLIT
st.set_page_config(page_title="RAPPORTS CLUBS - Datafoot", layout="wide")

# --- CORPS PRINCIPAL
st.markdown("## 📊 Rapports Clubs")

# --- FILTRE : SAISON
selected_saison = st.selectbox("Saison", options=["2025", "2024", "2023"], index=0)

# --- RÉCUPÉRATION DES DONNÉES
df_clubs = get_rapport_clubs(saison=selected_saison)

# --- AFFICHAGE TABLEAU
st.dataframe(df_clubs, use_container_width=True, hide_index=True)
