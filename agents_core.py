import os
import openai
from datetime import datetime, date
from simulateur_core import get_classement_dynamique, trier_et_numeroter, load_championnats

def analyser_et_executer_classement(question: str):
    """
    Reçoit une question utilisateur.
    Retourne un résumé textuel + un dataframe (ou None).
    Affiche toujours les éléments extraits, même en cas d’erreur.
    """

    # Charger la liste des championnats pour guider GPT
    df_champs = load_championnats()
    liste_championnats = df_champs["NOM_CHAMPIONNAT"].dropna().unique().tolist()

    # Extraction GPT (guidée par les noms valides)
    result = extraire_parametres_demande(question, liste_championnats)

    if "error" in result:
        return f"❌ Erreur d'extraction : {result['error']}", None

    # Récupération des éléments
    intent = result.get("intent", "")
    championnat = result.get("championnat", "")
    poule = result.get("poule", "")
    date_str = result.get("date", "").strip()

    # Fallback date
    if not date_str or date_str.lower() in ["aujourd’hui", "aujourd'hui", "ce jour", "today"]:
        date_str = str(date.today())

    # Résumé utilisateur
    resume_extrait = (
        f"- 🎯 **Intent** : {intent or '❓'}\n"
        f"- 🏆 **Championnat** : {championnat or '—'}\n"
        f"- 🅿️ **Poule** : {poule or '—'}\n"
        f"- 📅 **Date** : {date_str or '—'}\n"
    )

    # Validation date
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return f"{resume_extrait}\n❌ 📅 Date invalide : `{date_str}` (format attendu : AAAA-MM-JJ)", None

    # Validation championnat
    try:
        id_champ = int(get_id_championnat(championnat))
    except:
        return f"{resume_extrait}\n❌ 🏆 Championnat non reconnu : `{championnat}`", None

    # Vérification de l’intention
    if intent.lower() != "classement":
        return f"{resume_extrait}\n❌ Intention non supportée : `{intent}`", None

    # Calcul du classement
    try:
        df = get_classement_dynamique(
            champ_id=id_champ,
            date_limite=date_str,
            poule=poule if poule else None
        )
        df_final = trier_et_numeroter(df)
        resume = (
            f"{resume_extrait}\n✅ Classement généré pour **{championnat.upper()}**"
            f"{f' poule {poule.upper()}' if poule else ''} au **{date_str}**"
        )
        return resume, df_final

    except Exception as e:
        return f"{resume_extrait}\n❌ Erreur lors du calcul du classement : {str(e)}", None


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

def extraire_parametres_demande(question: str, liste_championnats: list[str], model="gpt-4", temperature=0.2) -> dict:
    """
    Envoie une requête à GPT pour extraire les paramètres structurés d'une question utilisateur.
    Le modèle doit obligatoirement choisir le championnat parmi la liste fournie.
    Retourne un dictionnaire avec : intent, championnat, poule, date.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Clé OPENAI_API_KEY non trouvée.")

    client = openai.OpenAI(api_key=api_key)

    # Construction du prompt système
    system_prompt = (
        "Tu es un assistant Datafoot. Ton rôle est d'extraire des requêtes utilisateur un dictionnaire JSON structuré "
        "contenant les clés suivantes :\n"
        "- intent : ex 'classement'\n"
        "- championnat : un nom EXACT parmi la liste fournie ci-dessous\n"
        "- poule : une lettre majuscule si présente (ex: A, B...), sinon null ou vide\n"
        "- date : au format AAAA-MM-JJ si présente, sinon null ou vide\n\n"
        "Ne commente pas. Ne reformule pas. Réponds uniquement avec un objet JSON valide.\n\n"
        "Voici la liste des championnats valides (choisis exclusivement parmi eux) :\n"
    )
    system_prompt += "\n".join([f"- {nom}" for nom in liste_championnats])

    # Appel à l'API
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=temperature,
        max_tokens=300
    )

    try:
        result = json.loads(completion.choices[0].message.content.strip())
        return result
    except Exception as e:
        return {
            "error": f"Erreur d'analyse JSON : {str(e)}",
            "raw": completion.choices[0].message.content
        }

    except Exception as e:
        return {"error": f"Erreur d'analyse JSON : {str(e)}", "raw": completion.choices[0].message.content}

