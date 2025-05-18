import streamlit as st
from agents_core import analyser_et_executer_classement

st.set_page_config(page_title="Agent GPT – Datafoot", layout="wide")
st.title("🧠 Agent GPT – Analyse et Classement")

prompt = st.text_area(
    "Pose une question à l'agent Datafoot",
    height=200,
    placeholder="Ex : Quel est le classement U17 poule C au 15 mars 2024 ?"
)

if st.button("📊 Lancer l’analyse et le calcul") and prompt:
    try:
        with st.spinner("🤖 Traitement de la demande..."):
            message, df = analyser_et_executer_classement(prompt)

        st.markdown(message)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Erreur générale : {e}")

