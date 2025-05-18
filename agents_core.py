import openai
import os
import streamlit as st

def get_id_championnat(nom):
    import json
    import re
    from simulateur_core import load_championnats

    nom = nom.upper().strip()
    match = re.match(r"(.*?)\s?(POULE|GROUPE)?\s?([A-Z])?$", nom)
    nom_champ = match.group(1).strip() if match else nom
    poule = match.group(3) if match and match.group(3) else None

    df = load_championnats()
    df["NOM_CLEAN"] = df["NOM_CHAMPIONNAT"].str.upper().str.replace("NATIONAL", "NAT").str.replace("\s", "", regex=True)
    nom_clean = nom_champ.replace("NATIONAL", "NAT").replace(" ", "")

    filtres = df[df["NOM_CLEAN"].str.contains(nom_clean)]

    if filtres.empty:
        return "Aucun championnat correspondant trouvé."
    elif len(filtres) == 1:
        id_championnat = int(filtres.iloc[0]["ID_CHAMPIONNAT"])
        if poule:
            return json.dumps({"id_championnat": id_championnat, "poule": poule})
        return str(id_championnat)
    else:
        options = filtres[["ID_CHAMPIONNAT", "NOM_CHAMPIONNAT"]].drop_duplicates()
        message = "Plusieurs championnats correspondent à \"{}\" :\n".format(nom_champ)
        for _, row in options.iterrows():
            message += f"- {row['NOM_CHAMPIONNAT']} (ID {row['ID_CHAMPIONNAT']})\n"
        message += "Peux-tu préciser lequel tu veux ?"
        return message


def get_id_equipe(nom: str) -> int:
    """
    Retourne l'ID_EQUIPE à partir d'un nom d'équipe connu.
    Ce mapping est temporaire, à remplacer par une requête dynamique.
    """
    mapping = {
        "RC LENS": 101,
        "OLYMPIQUE MARSEILLE": 102,
        "PSG": 103,
        "AS MONACO": 104
    }
    return mapping.get(nom.upper())

def construire_system_prompt():
    return (
        "Tu es un agent conversationnel spécialisé dans les règlements et données des championnats de football amateur en France. "
        "Tu fais partie de la plateforme Datafoot. Tu aides à comprendre des règles, des formats, et à structurer des données textuelles liées aux compétitions."
    )

def appeler_agent_gpt(question, model="gpt-4", temperature=0.4):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ Clé OPENAI_API_KEY non trouvée dans les variables d'environnement.")
    
    client = openai.OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": construire_system_prompt()},
        {"role": "user", "content": question}
    ]
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=1000
    )

def extraire_parametres_demande(question: str, model="gpt-4", temperature=0.2) -> dict:
    """
    Envoie une requête à GPT pour extraire les paramètres structurés d'une question utilisateur.
    Retourne un dictionnaire avec : intent, championnat, poule, date.
    """
    import openai
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Clé OPENAI_API_KEY non trouvée.")

    client = openai.OpenAI(api_key=api_key)

    system_prompt = (
        "Tu es un assistant Datafoot. Quand on te pose une question, tu dois en extraire les paramètres "
        "structurés dans un dictionnaire JSON. Le dictionnaire doit contenir les clés suivantes :\n"
        "- intent (ex: 'classement')\n"
        "- championnat (ex: 'U17')\n"
        "- poule (ex: 'C', facultatif)\n"
        "- date (au format 'AAAA-MM-JJ', facultatif)\n"
        "Ne commente rien. Ne justifie rien. Réponds uniquement avec un objet JSON bien formé."
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=temperature,
        max_tokens=300
    )

    import json
    try:
        result = json.loads(completion.choices[0].message.content.strip())
        return result
    except Exception as e:
        return {"error": f"Erreur d'analyse JSON : {str(e)}", "raw": completion.choices[0].message.content}

