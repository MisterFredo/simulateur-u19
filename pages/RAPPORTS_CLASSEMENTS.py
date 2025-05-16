import streamlit as st
import sys
import os

# --- CHEMIN D'IMPORT CORE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- CONFIG
st.set_page_config(page_title="RAPPORTS CLASSEMENTS - Datafoot", layout="wide")

# --- TITRE
st.markdown("## 🏆 Classements par performance")

# --- FILTRES DE BASE
col1, col2 = st.columns(2)

with col1:
    selected_saison = st.selectbox("Saison", ["2025", "2024", "2023"], index=0)

with col2:
    selected_categorie = st.selectbox("Catégorie", ["SENIOR", "U19", "U18", "U17", "U16", "U15"], index=0)

# --- PLACEHOLDER
st.info("Sélectionnez une saison et une catégorie pour afficher le classement.")
