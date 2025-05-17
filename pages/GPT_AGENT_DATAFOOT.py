import streamlit as st
from agents_core import appeler_agent_gpt

st.set_page_config(page_title="Agent GPT – Datafoot", layout="wide")
st.title("🤖 Agent GPT – Datafoot LABO")

prompt = st.text_area(
    "Pose une question à l'agent Datafoot",
    height=200,
    placeholder="Ex : Quels critères pour départager des équipes à égalité en U17 ?"
)

if st.button("Envoyer", type="primary") and prompt:
    try:
        with st.spinner("Réflexion en cours..."):
            response = appeler_agent_gpt(prompt)
            st.success("Réponse générée :")
            st.markdown(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API : {e}")

