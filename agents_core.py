# --- agents_core.py ---

def get_id_championnat(nom):
    """
    Extrait l'identifiant du championnat à partir d'un nom partiel (ex: 'U19', 'N3', 'N2 D', etc.).
    Peut aussi renvoyer le nom de la poule associé s'il est inclus dans la requête.
    """
    import re
    from simulateur_core import load_championnats

    # Extraction du texte et de la poule éventuelle
    nom = nom.upper().strip()
    match = re.match(r"(.*?)\s?(POULE|GROUPE)?\s?([A-Z])?$", nom)

    nom_champ = match.group(1).strip() if match else nom
    poule = match.group(3) if match and match.group(3) else None

    # Chargement des noms disponibles
    df = load_championnats()
    df["NOM_CLEAN"] = df["NOM_CHAMPIONNAT"].str.upper().str.replace("NATIONAL", "NAT").str.replace("\s", "", regex=True)
    nom_clean = nom_champ.replace("NATIONAL", "NAT").replace(" ", "")

    filtres = df[df["NOM_CLEAN"].str.contains(nom_clean)]
    if filtres.empty:
        return "Aucun championnat correspondant trouvé."

    id_championnat = int(filtres.iloc[0]["ID_CHAMPIONNAT"])
    if poule:
        return json.dumps({"id_championnat": id_championnat, "poule": poule})
    return str(id_championnat)

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
