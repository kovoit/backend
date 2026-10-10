"""Lieux connus de Lomé (coordonnées approximatives) et itinéraires de démonstration."""

LIEUX = {
    "franciscain": {"libelle": "Adidogomé · Carrefour Franciscain", "lat": 6.1676, "lng": 1.1592},
    "universite": {"libelle": "Université de Lomé · Entrée sud", "lat": 6.1745, "lng": 1.212},
    "zongo": {"libelle": "Agoè · Carrefour Zongo", "lat": 6.228, "lng": 1.2033},
    "grand_marche": {"libelle": "Grand Marché (Assigamé)", "lat": 6.1275, "lng": 1.2225},
    "kpota": {"libelle": "Bè · Kpota", "lat": 6.142, "lng": 1.242},
    "baguida": {"libelle": "Baguida · Centre", "lat": 6.16, "lng": 1.324},
    "chu": {"libelle": "Tokoin · CHU Sylvanus Olympio", "lat": 6.134, "lng": 1.216},
    "hedzranawoe": {"libelle": "Hédzranawoé · Marché", "lat": 6.161, "lng": 1.236},
    "avedji": {"libelle": "Carrefour Avédji", "lat": 6.188, "lng": 1.181},
    "totsi": {"libelle": "Carrefour Totsi", "lat": 6.181, "lng": 1.196},
    "deckon": {"libelle": "Déckon", "lat": 6.131, "lng": 1.222},
    "kegue": {"libelle": "Kégué · Stade", "lat": 6.168, "lng": 1.252},
    "nyekonakpoe": {"libelle": "Nyékonakpoè", "lat": 6.135, "lng": 1.205},
    "port": {"libelle": "Port autonome de Lomé", "lat": 6.137, "lng": 1.284},
}

# (départ, points de prise en charge, arrivée)
ITINERAIRES = [
    ("franciscain", ["avedji", "totsi"], "universite"),
    ("zongo", ["universite"], "grand_marche"),
    ("baguida", ["kegue", "hedzranawoe"], "chu"),
    ("kpota", ["deckon"], "nyekonakpoe"),
    ("avedji", ["totsi", "universite", "chu"], "port"),
    ("hedzranawoe", ["kegue"], "grand_marche"),
]


def itineraire(index: int) -> dict:
    depart, points, arrivee = ITINERAIRES[index % len(ITINERAIRES)]
    return {
        "depart": LIEUX[depart],
        "points": [LIEUX[nom] for nom in points],
        "arrivee": LIEUX[arrivee],
    }
