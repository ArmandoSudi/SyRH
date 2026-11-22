"""Which pieces an event requires, and whether it has them (documents on events D13 to D18).

The required pieces are the PieceRequise rows of the event's kind open on its
date (D13). One is satisfied by an active link to a non-retired document whose
type has the same code (D14). An event is complete when every mandatory piece is
satisfied; optional ones never block (D15). Phase 2.11 calls pieces_manquantes()
to refuse validating an incomplete event.

Confidential documents count for everyone but are listed only to their readers
(D18): pass the user to get the lists filtered.
"""

from dataclasses import dataclass, field
from datetime import date

from django.db.models import Model

from apps.referentiels.models import PieceRequise

from .evenements import EvenementAgent, evenement_de, evenements_de, prefetch_evenements
from .models import Agent, Document


@dataclass
class EtatPiece:
    code: str
    nom: str
    obligatoire: bool
    satisfaite: bool
    documents: list[Document] = field(default_factory=list)  # those the user may read
    confidentielles: int = 0  # the others


@dataclass
class EtatPieces:
    evenement: EvenementAgent
    pieces: list[EtatPiece]
    autres: list[Document]  # attached, matching no requirement, readable
    autres_confidentielles: int
    liens: dict[int, int] = field(default_factory=dict)  # document id -> active link id

    @property
    def manquantes(self) -> list[str]:
        return [p.code for p in self.pieces if p.obligatoire and not p.satisfaite]

    @property
    def complet(self) -> bool:
        return not self.manquantes


def _ouverte(row: PieceRequise, jour: date) -> bool:
    return row.date_ouverture <= jour and (row.date_fermeture is None or jour < row.date_fermeture)


def _exigences(evenements: list[EvenementAgent]) -> list[PieceRequise]:
    kinds = {e.evenement for e in evenements if e.evenement}
    if not kinds:
        return []
    return list(
        PieceRequise.objects.filter(evenement__in=kinds)
        .select_related("type_document")
        .order_by("-obligatoire", "type_document__nom", "date_ouverture")
    )


def _etat(evenement: EvenementAgent, exigences, lisibles: set[int] | None) -> EtatPieces:
    actifs = evenement.liens_actifs()
    documents = [lien.document for lien in actifs if not lien.document.retire]
    readable = (lambda doc: True) if lisibles is None else (lambda doc: doc.pk in lisibles)
    pieces, codes = [], set()
    if evenement.evenement:
        for row in exigences:
            code = row.type_document.code
            if row.evenement != evenement.evenement or code in codes:
                continue
            if not _ouverte(row, evenement.date):
                continue
            codes.add(code)
            matching = [doc for doc in documents if doc.type_document.code == code]
            pieces.append(
                EtatPiece(
                    code=code,
                    nom=row.type_document.nom,
                    obligatoire=row.obligatoire,
                    satisfaite=bool(matching),
                    documents=[doc for doc in matching if readable(doc)],
                    confidentielles=sum(1 for doc in matching if not readable(doc)),
                )
            )
    others = [doc for doc in documents if doc.type_document.code not in codes]
    return EtatPieces(
        evenement=evenement,
        pieces=pieces,
        autres=[doc for doc in others if readable(doc)],
        autres_confidentielles=sum(1 for doc in others if not readable(doc)),
        liens={lien.document_id: lien.pk for lien in actifs},
    )


def _lisibles(agent: Agent, user) -> set[int] | None:
    if user is None:
        return None
    return set(Document.objects.filter(agent=agent).lisibles_par(user).values_list("pk", flat=True))


def etats_pieces(agent: Agent, user=None) -> list[EtatPieces]:
    """Every event of an agent with its pieces, newest first, in a fixed number of
    queries when the agent comes from prefetch_evenements() (D16)."""
    evenements = evenements_de(agent)
    exigences = _exigences(evenements)
    lisibles = _lisibles(agent, user)
    return [_etat(e, exigences, lisibles) for e in evenements]


def etats_pieces_de(agent_id: int, user=None) -> list[EtatPieces]:
    agent = prefetch_evenements(Agent.objects.filter(pk=agent_id)).get()
    return etats_pieces(agent, user)


def etat_pieces(objet: Model, user=None) -> EtatPieces:
    """The pieces of one event (a contract, an assignment, a classification)."""
    evenement = evenement_de(objet)
    return _etat(evenement, _exigences([evenement]), _lisibles(objet.agent, user))


def pieces_manquantes(objet: Model) -> list[str]:
    """The codes of the mandatory pieces an event still misses; empty when complete.
    Phase 2.11 refuses to validate an event while this is not empty (D15, D16)."""
    return etat_pieces(objet).manquantes
