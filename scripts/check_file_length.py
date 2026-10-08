"""Vérifie qu'aucun fichier Python du projet ne dépasse 200 lignes (migrations exclues)."""

import sys
from pathlib import Path

LIMITE = 200
RACINE = Path(__file__).resolve().parent.parent
DOSSIERS = ("apps", "kovoit", "scripts")
EXCLUS = {"migrations", "__pycache__", ".venv"}


def fichiers_python():
    for dossier in DOSSIERS:
        for chemin in (RACINE / dossier).rglob("*.py"):
            if not EXCLUS.intersection(chemin.parts):
                yield chemin


def main() -> int:
    trop_longs = []
    for chemin in fichiers_python():
        with chemin.open(encoding="utf-8") as fichier:
            nb_lignes = sum(1 for _ in fichier)
        if nb_lignes > LIMITE:
            trop_longs.append((chemin.relative_to(RACINE), nb_lignes))

    if not trop_longs:
        print(f"OK : aucun fichier ne dépasse {LIMITE} lignes.")
        return 0

    print(f"ERREUR : fichiers de plus de {LIMITE} lignes (à découper en package) :")
    for chemin, nb_lignes in sorted(trop_longs):
        print(f"  {chemin} : {nb_lignes} lignes")
    return 1


if __name__ == "__main__":
    sys.exit(main())
