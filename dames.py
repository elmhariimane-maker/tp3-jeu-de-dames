"""Le jeu de dames en objets : cases, pièces, plateau et partie.

Règles du jeu de dames international (plateau de 10 x 10), simplifiées : une seule prise par
coup (pas de rafle) et pas de règle de la majorité.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from exceptions import CoupInvalideError

COLONNES = "abcdefghij"
TAILLE = 10
DIAGONALES = [(1, 1), (-1, 1), (1, -1), (-1, -1)]


def adversaire(couleur: str) -> str:
    """La couleur de l'autre joueur."""
    return "noir" if couleur == "blanc" else "blanc"


# --- Étape 1 : la case ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Case:
    """Une case, de a1 à j10. Immuable : on peut la hacher et s'en servir comme clé."""
    colonne: str
    ligne: int

    def __post_init__(self):
        """Refuse une colonne hors de a..j ou une ligne hors de 1..10 (ValueError)."""
        if not isinstance(self.colonne, str) or len(self.colonne) != 1 or self.colonne not in COLONNES:
            raise ValueError(f"colonne invalide : {self.colonne!r}")
        if not isinstance(self.ligne, int) or isinstance(self.ligne, bool) or not (1 <= self.ligne <= TAILLE):
            raise ValueError(f"ligne invalide : {self.ligne!r}")

    @classmethod
    def depuis_nom(cls, nom: str) -> "Case":
        """Case.depuis_nom("c3") donne Case('c', 3) ; un nom mal formé lève ValueError."""
        try:
            col = nom[0]
            lig = int(nom[1:])
            return cls(col, lig)
        except (ValueError, IndexError, TypeError):
            raise ValueError(f"nom de case invalide : {nom!r}") from None

    @property
    def est_noire(self) -> bool:
        """On ne joue que sur les cases noires ; a1 est noire."""
        return (COLONNES.index(self.colonne) + self.ligne) % 2 == 1

    def decaler(self, dc: int, dl: int) -> "Case | None":
        """La case située dc colonnes et dl lignes plus loin, ou None si on sort du plateau."""
        nouv_col_idx = COLONNES.index(self.colonne) + dc
        nouv_ligne = self.ligne + dl
        if 0 <= nouv_col_idx < TAILLE and 1 <= nouv_ligne <= TAILLE:
            return Case(COLONNES[nouv_col_idx], nouv_ligne)
        return None

    def __str__(self) -> str:
        return f"{self.colonne}{self.ligne}"


def en_case(valeur: "Case | str") -> Case:
    """Accepte une Case ou un nom comme "c3"."""
    return valeur if isinstance(valeur, Case) else Case.depuis_nom(valeur)


def ordre(case: Case) -> tuple[int, int]:
    """Clé de tri : ligne par ligne, puis de gauche à droite."""
    return case.ligne, COLONNES.index(case.colonne)





# --- Étape 2 : les pièces ------------------------------------------------------------------------
class Piece(ABC):
    """Une pièce : une couleur qui ne change jamais. Elle ne connaît pas sa case :
    c'est le plateau qui sait où sont les pièces."""

    COULEURS = ("blanc", "noir")
    LETTRE = "?"          # redéfinis par chaque sous-classe
    NOM = "pièce"
    FEMININ = False

    def __init__(self, couleur: str):
        """Refuse une couleur autre que "blanc" ou "noir" (ValueError)."""
        if couleur not in self.COULEURS:
            raise ValueError(f"couleur invalide : {couleur!r}")
        self._couleur = couleur

    @property
    def couleur(self) -> str:
        """Lecture seule : pas de setter."""
        return self._couleur

    @property
    def sens(self) -> int:
        """Le sens de la marche : +1 (vers la ligne 10) pour les blancs, -1 pour les noirs."""
        return 1 if self._couleur == "blanc" else -1

    @property
    def symbole(self) -> str:
        """La lettre en majuscule pour les blancs, en minuscule pour les noirs."""
        return self.LETTRE.upper() if self._couleur == "blanc" else self.LETTRE.lower()

    def est_adverse(self, autre: "Piece | None") -> bool:
        """Vrai si autre est une pièce de l'autre couleur (faux pour None)."""
        return autre is not None and autre.couleur != self._couleur

    @abstractmethod
    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        """Les cases où la pièce peut aller depuis case, sans prendre."""

    @abstractmethod
    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        """Les prises possibles depuis case : {case d'arrivée: case de la pièce prise}."""

    def promouvoir(self, case: Case) -> "Piece":
        """La pièce qui occupe case après le coup. Par défaut, la pièce reste la même."""
        return self

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._couleur!r})"

    def __str__(self) -> str:
        if self.FEMININ:
            couleur_str = "blanche" if self._couleur == "blanc" else "noire"
        else:
            couleur_str = self._couleur
        return f"{self.NOM} {couleur_str}"



# --- Étape 3 : le plateau ------------------------------------------------------------------------
class Plateau:
    """Le plateau A des pièces (composition), rangées dans un dict privé case -> pièce."""

    def __init__(self):
        self._pieces: dict[Case, Piece] = {}

    @classmethod
    def depuis_dict(cls, pieces: dict[str, str]) -> "Plateau":
        """Constructeur alternatif : Plateau.depuis_dict({"c3": "P", "f6": "d"}).
        P = pion, D = dame ; majuscule pour les blancs, minuscule pour les noirs."""
        plateau = cls()
        for nom, lettre in pieces.items():
            couleur = "blanc" if lettre.isupper() else "noir"
            classe = Pion if lettre.upper() == "P" else Dame
            plateau.placer(nom, classe(couleur))
        return plateau

    @classmethod
    def position_initiale(cls) -> "Plateau":
        """Un pion sur chaque case noire : blancs en lignes 1 à 4, noirs en lignes 7 à 10."""
        plateau = cls()
        for ligne in (1, 2, 3, 4):
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                if case.est_noire:
                    plateau.placer(case, Pion("blanc"))
        for ligne in (7, 8, 9, 10):
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                if case.est_noire:
                    plateau.placer(case, Pion("noir"))
        return plateau

    def placer(self, case: "Case | str", piece: Piece) -> None:
        """Pose une pièce. ValueError si la case est blanche ou déjà occupée."""
        c = en_case(case)
        if not c.est_noire:
            raise ValueError(f"{c} est une case blanche")
        if c in self._pieces:
            raise ValueError(f"{c} est déjà occupée")
        self._pieces[c] = piece

    def __getitem__(self, case: "Case | str") -> "Piece | None":
        """plateau["c3"] : la pièce sur la case, ou None si elle est vide."""
        return self._pieces.get(en_case(case))

    def __contains__(self, case: "Case | str") -> bool:
        """"c3" in plateau : vrai si la case est occupée."""
        return en_case(case) in self._pieces

    def __len__(self) -> int:
        """Le nombre de pièces sur le plateau."""
        return len(self._pieces)

    def __iter__(self):
        """Parcourt les cases occupées, ligne par ligne, de gauche à droite."""
        return iter(sorted(self._pieces, key=ordre))

    def compter(self, couleur: str) -> int:
        return sum(1 for case in self if self[case].couleur == couleur)

    # --- Étape 6
    def prises_possibles(self, couleur: str) -> dict[Case, dict[Case, Case]]:
        """Toutes les prises d'un joueur : {départ: {arrivée: pièce prise}}, seulement pour les
        pièces qui peuvent prendre."""
        raise NotImplementedError("à compléter")

    def coups_possibles(self, couleur: str) -> list[tuple[Case, Case]]:
        """Les coups autorisés, triés. S'il existe des prises, seules les prises comptent."""
        raise NotImplementedError("à compléter")

    def deplacer(self, depart: "Case | str", arrivee: "Case | str") -> "Piece | None":
        """Joue un coup, renvoie la pièce prise ou None. Vérifier d'abord, modifier ensuite."""
        raise NotImplementedError("à compléter")

# --- Étape 8
    def vers_dict(self) -> dict[str, str]:
        """L'inverse de depuis_dict : {"c3": "P", "f6": "d", ...}, dans l'ordre du plateau."""
        return {str(case): self[case].symbole for case in self}


    # --- Affichage (fourni)
    def __repr__(self) -> str:
        return f"<Plateau : {self.compter('blanc')} blancs, {self.compter('noir')} noirs>"

    def __str__(self) -> str:
        lignes = []
        for ligne in range(TAILLE, 0, -1):
            cases = []
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                piece = self[case]
                cases.append(piece.symbole if piece else "." if case.est_noire else " ")
            lignes.append(f"{ligne:>2}  " + " ".join(cases))
        lignes.append("    " + " ".join(COLONNES))
        return "\n".join(lignes)



        # --- Étape 6
    def prises_possibles(self, couleur: str) -> dict[Case, dict[Case, Case]]:
        """Toutes les prises d'un joueur : {départ: {arrivée: pièce prise}}, seulement pour les
        pièces qui peuvent prendre."""
        resultat = {}
        for case in self:
            piece = self[case]
            if piece.couleur == couleur:
                captures = piece.prises(case, self)
                if captures:
                    resultat[case] = captures
        return resultat

    def coups_possibles(self, couleur: str) -> list[tuple[Case, Case]]:
        """Les coups autorisés, triés. S'il existe des prises, seules les prises comptent."""
        prises = self.prises_possibles(couleur)
        coups = []
        if prises:
            for depart, captures in prises.items():
                for arrivee in captures:
                    coups.append((depart, arrivee))
        else:
            for case in self:
                piece = self[case]
                if piece.couleur == couleur:
                    for arrivee in piece.deplacements(case, self):
                        coups.append((case, arrivee))
        return sorted(coups, key=lambda coup: (ordre(coup[0]), ordre(coup[1])))

    def deplacer(self, depart: "Case | str", arrivee: "Case | str") -> "Piece | None":
        """Joue un coup, renvoie la pièce prise ou None. Vérifier d'abord, modifier ensuite."""
        c_dep = en_case(depart)
        c_arr = en_case(arrivee)
        piece = self[c_dep]

        if piece is None:
            raise CoupInvalideError(depart, arrivee, "aucune pièce sur la case de départ")

        prises_joueur = self.prises_possibles(piece.couleur)
        piece_prise = None

        if prises_joueur:
            prises_piece = prises_joueur.get(c_dep, {})
            if c_arr not in prises_piece:
                raise CoupInvalideError(depart, arrivee, "la prise est obligatoire")
            case_prise = prises_piece[c_arr]
            piece_prise = self._pieces[case_prise]
        else:
            if c_arr not in piece.deplacements(c_dep, self):
                raise CoupInvalideError(depart, arrivee, "déplacement interdit")

        del self._pieces[c_dep]
        if piece_prise is not None:
            del self._pieces[case_prise]
        self._pieces[c_arr] = piece.promouvoir(c_arr)

        return piece_prise


    # --- Étape 8
    def vers_dict(self) -> dict[str, str]:
        """L'inverse de depuis_dict : {"c3": "P", "f6": "d", ...}, dans l'ordre du plateau."""
        return {str(case): self[case].symbole for case in self}


    # --- Affichage (fourni)
    def __repr__(self) -> str:
        return f"<Plateau : {self.compter('blanc')} blancs, {self.compter('noir')} noirs>"

    def __str__(self) -> str:
        lignes = []
        for ligne in range(TAILLE, 0, -1):
            cases = []
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                piece = self[case]
                cases.append(piece.symbole if piece else "." if case.est_noire else " ")
            lignes.append(f"{ligne:>2}  " + " ".join(cases))
        lignes.append("    " + " ".join(COLONNES))
        return "\n".join(lignes)


# --- Étape 4 : le pion ---------------------------------------------------------------------------
class Pion(Piece):
    LETTRE = "P"
    NOM = "pion"

    def deplacements(self, case, plateau):
        """Une case en diagonale, vers l'avant, si elle est libre."""
        possibles = set()
        for dc in (-1, 1):
            cible = case.decaler(dc, self.sens)
            if cible is not None and plateau[cible] is None:
                possibles.add(cible)
        return possibles

    def prises(self, case, plateau):
        """Sauter une pièce adverse voisine (avant ou arrière) vers la case libre derrière."""
        captures = {}
        for dc, dl in DIAGONALES:
            milieu = case.decaler(dc, dl)
            arrivee = case.decaler(2 * dc, 2 * dl)
            if arrivee is not None and plateau[arrivee] is None:
                if milieu is not None and self.est_adverse(plateau[milieu]):
                    captures[arrivee] = milieu
        return captures
     # --- Étape 6
    def promouvoir(self, case):
        """Sur la dernière ligne (10 pour les blancs, 1 pour les noirs), le pion devient dame."""
        ligne_promo = TAILLE if self._couleur == "blanc" else 1
        if case.ligne == ligne_promo:
            return Dame(self._couleur)
        return self



# --- Étape 5 : la dame ---------------------------------------------------------------------------
class Dame(Piece):
    LETTRE = "D"
    NOM = "dame"
    FEMININ = True

    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        """Toutes les cases libres en diagonale jusqu'au premier obstacle."""
        possibles = set()
        for dc, dl in DIAGONALES:
            suivante = case.decaler(dc, dl)
            while suivante is not None and plateau[suivante] is None:
                possibles.add(suivante)
                suivante = suivante.decaler(dc, dl)
        return possibles

    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        """Prise à distance en diagonale : cases libres, une pièce adverse, puis cases libres derrière."""
        captures = {}
        for dc, dl in DIAGONALES:
            suivante = case.decaler(dc, dl)
            while suivante is not None and plateau[suivante] is None:
                suivante = suivante.decaler(dc, dl)

            if suivante is not None and self.est_adverse(plateau[suivante]):
                piece_prise = suivante
                derriere = piece_prise.decaler(dc, dl)
                while derriere is not None and plateau[derriere] is None:
                    captures[derriere] = piece_prise
                    derriere = derriere.decaler(dc, dl)
        return captures

# --- Étape 7 : la partie -------------------------------------------------------------------------
@dataclass(frozen=True)
class Coup:
    """Un coup joué. Gelé : un coup joué ne change plus."""
    numero: int
    couleur: str
    depart: str
    arrivee: str
    prise: bool = False

    def __str__(self) -> str:
        """Notation des dames : "1. c3-d4" pour un déplacement, "4. d4xf6" pour une prise."""
        symbole = "x" if self.prise else "-"
        return f"{self.numero}. {self.depart}{symbole}{self.arrivee}"


class Partie:
    """Une partie A un plateau et un historique (composition) et sait à qui c'est le tour."""

    def __init__(self, plateau: "Plateau | None" = None):
        self.plateau = plateau if plateau is not None else Plateau.position_initiale()
        self.trait = "blanc"                  # la couleur qui doit jouer
        self.historique: list[Coup] = []

    def jouer(self, depart: str, arrivee: str) -> Coup:
        """Vérifie le trait, joue, note le coup, passe la main à l'adversaire."""
        c_dep = en_case(depart)
        piece = self.plateau[c_dep]
        if piece is not None and piece.couleur != self.trait:
            msg = "c'est aux blancs de jouer" if self.trait == "blanc" else "c'est aux noirs de jouer"
            raise CoupInvalideError(depart, arrivee, msg)

        piece_prise = self.plateau.deplacer(depart, arrivee)
        coup = Coup(
            numero=len(self.historique) + 1,
            couleur=self.trait,
            depart=str(c_dep),
            arrivee=str(en_case(arrivee)),
            prise=piece_prise is not None,
        )
        self.historique.append(coup)
        self.trait = adversaire(self.trait)
        return coup

    @property
    def gagnant(self) -> "str | None":
        """Celui qui a le trait et ne peut plus jouer a perdu : la couleur gagnante, ou None."""
        if not self.plateau.coups_possibles(self.trait):
            return adversaire(self.trait)
        return None


 # --- Étape 8
    def sauvegarder(self, chemin) -> None:
        """Écrit la partie en JSON : {"trait": ..., "pieces": {"c3": "P", ...}}."""
        donnees = {
            "trait": self.trait,
            "pieces": self.plateau.vers_dict(),
        }
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)

    @classmethod
    def charger(cls, chemin) -> "Partie":
        """Constructeur alternatif : recrée une partie écrite par sauvegarder."""
        with open(chemin, "r", encoding="utf-8") as f:
            donnees = json.load(f)
        plateau = Plateau.depuis_dict(donnees["pieces"])
        partie = cls(plateau)
        partie.trait = donnees["trait"]
        return partie
