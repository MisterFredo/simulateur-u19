import streamlit as st
import openai

st.set_page_config(page_title="Agent GPT – Datafoot", layout="wide")

# Titre principal
st.title("🤖 Agent GPT – Datafoot LABO")

# Champ d'entrée utilisateur
prompt = st.text_area("Pose une question à l'agent Datafoot", height=200, placeholder="Ex : Quels critères pour départager des équipes à égalité en U17 ?")

# Bouton pour envoyer
if st.button("Envoyer", type="primary") and prompt:
    try:
        with st.spinner("Réflexion en cours..."):
            client = openai.OpenAI(api_key=st.secrets["openai_api_key"])
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Tu es un assistant spécialisé dans l'analyse des championnats de football amateur en France, connecté à l'univers Datafoot."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800,
            )

            st.success("Réponse générée :")
            st.markdown(response.choices[0].message.content)

    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API : {e}")
