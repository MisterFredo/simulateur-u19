import streamlit as st

# --- Définir la configuration de la page principale ---
st.set_page_config(page_title="Datafoot", page_icon="⚽", layout="centered")

# --- Initialiser la page courante ---
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- Fonctions pour afficher les différentes sections ---
def afficher_accueil():
    st.title("Bienvenue sur Datafoot 👋")
    
    st.markdown("### Que souhaitez-vous faire ?")

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Voir Classement Officiel"):
        st.session_state.page = "classement"

with col2:
    if st.button("🔮 Lancer une Simulation"):
        st.session_state.page = "simulation"


    st.markdown("---")
    st.subheader("⚡ Accès rapides aux championnats")

    st.markdown("**Séniors**")
    if st.button("🏆 National"):
        st.session_state.page = "championnat_national"
    if st.button("🏆 National 2 (3 Poules)"):
        st.session_state.page = "championnat_n2"
    if st.button("🏆 National 3 (10 Poules)"):
        st.session_state.page = "championnat_n3"

    st.markdown("**Jeunes Nationaux**")
    if st.button("🎯 U19 National"):
        st.session_state.page = "championnat_u19"
    if st.button("🎯 U17 National"):
        st.session_state.page = "championnat_u17"

    st.markdown("**Jeunes Régionaux**")
    if st.button("🧢 U17 R1"):
        st.session_state.page = "championnat_u17r1"
    if st.button("🧢 U18 R1"):
        st.session_state.page = "championnat_u18r1"

def afficher_simulateur():
    # >>> Ici tu vas appeler la logique de simulateur.py <<<
    import simulateur
    simulateur.afficher_classement()  # Ou la fonction principale que tu veux utiliser

def afficher_classements_speciaux():
    # >>> Ici tu vas appeler la logique de simulateur_whatif.py <<<
    import pages.simulateur_whatif as simulateur_whatif
    simulateur_whatif.afficher_simulateur_whatif()  # Ou la fonction principale que tu veux utiliser

def afficher_championnat(championnat):
    st.title(f"🏆 Championnat : {championnat}")
    st.info(f"Chargement du championnat {championnat}...")
    # Tu pourras brancher ici ta logique spécifique par championnat
    # (Simuler directement, afficher classement, etc.)

# --- Navigation en fonction de la page active ---
if st.session_state.page == "home":
    afficher_accueil()

elif st.session_state.page == "classement":
    afficher_simulateur()

elif st.session_state.page == "simulation":
    afficher_classements_speciaux()

elif st.session_state.page == "championnat_national":
    afficher_championnat("National")

elif st.session_state.page == "championnat_n2":
    afficher_championnat("National 2")

elif st.session_state.page == "championnat_n3":
    afficher_championnat("National 3")

elif st.session_state.page == "championnat_u19":
    afficher_championnat("U19 National")

elif st.session_state.page == "championnat_u17":
    afficher_championnat("U17 National")

elif st.session_state.page == "championnat_u17r1":
    afficher_championnat("U17 R1")

elif st.session_state.page == "championnat_u18r1":
    afficher_championnat("U18 R1")
