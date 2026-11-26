"""Jouer aux dames à deux dans le terminal : chaque joueur tape son coup, comme c3 d4."""
from dames import Partie
from exceptions import ErreurDames


def lire_coup(texte: str) -> tuple[str, str]:
    """« c3 d4 », « c3-d4 » ou « d4xf6 » donnent ("c3", "d4"). Sinon ValueError."""
    morceaux = texte.replace("-", " ").replace("x", " ").split()
    if len(morceaux) != 2:
        raise ValueError("tapez deux cases, par exemple c3 d4")
    return morceaux[0], morceaux[1]


def main() -> int:
    partie = Partie()
    print(partie.plateau)
    while partie.gagnant is None:
        saisie = input(f"{partie.trait} > ").strip()
        if saisie == "quitter":
            print("Partie abandonnée.")
            return 0
        if saisie == "sauver":
            partie.sauvegarder("partie.json")
            print("Partie sauvegardée.")
            continue
        if saisie == "reprendre":
            try:
                partie = Partie.charger("partie.json")
                print("Partie reprise.")
                print(partie.plateau)
            except FileNotFoundError:
                print("Refusé : aucune sauvegarde trouvée.")
            continue
        try:
            depart, arrivee = lire_coup(saisie)
            coup = partie.jouer(depart, arrivee)
        except (ErreurDames, ValueError) as err:
            print(f"Refusé : {err}")
            continue
        print(coup)
        print(partie.plateau)

    gagnant_str = "Les blancs gagnent !" if partie.gagnant == "blanc" else "Les noirs gagnent !"
    print(gagnant_str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
