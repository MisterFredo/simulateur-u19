# --- agents_core.py ---

def get_id_championnat(nom: str) -> int:
    """
    Retourne l'ID_CHAMPIONNAT à partir d'un nom connu.
    Ce mapping peut évoluer dynamiquement par la suite.
    """
    mapping = {
        "U19": 6,
        "U17": 7,
        "N2": 4,
        "N3": 5
    }
    return mapping.get(nom.upper())

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
