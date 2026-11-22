"""The events of an agent's file that rest on documents (documents on events D7 to D12).

Every event model answers the same protocol: its kind (a PieceRequise.Evenement
value, or None when it belongs to the agent's hiring), its date, its agent and
its label. Kinds are computed from the agent's history, never stored (D12):
correcting a date changes them. Later phases (dependants, Milestone 3) add their
models to MODELES_EVENEMENT and to evenements_de().
"""

from dataclasses import dataclass
from datetime import date

from django.db.models import Model, Prefetch

from apps.referentiels.models import Evenement

from .models import Affectation, Agent, Classement, Contrat, PieceJointe


@dataclass
class EvenementAgent:
    """One event of an agent: the row, its model name, kind, date and label."""

    objet: Model
    modele: str
    evenement: str | None
    date: date

    @property
    def cle(self) -> str:
        return f"{self.modele}-{self.objet.pk}"

    @property
    def libelle(self) -> str:
        return str(self.objet)

    @property
    def evenement_libelle(self) -> str:
        return Evenement(self.evenement).label if self.evenement else "Engagement (inclus)"

    def liens_actifs(self) -> list[PieceJointe]:
        return [lien for lien in self.objet.pieces_jointes.all() if lien.date_retrait is None]


def prefetch_evenements(queryset):
    """Agents with everything evenements_de() and etats_pieces() read, in a fixed
    number of queries (D6, D16)."""
    liens = PieceJointe.objects.select_related("document__type_document").order_by(
        "date_creation", "id"
    )
    return queryset.prefetch_related(
        Prefetch(
            "contrats",
            queryset=Contrat.objects.select_related("type_contrat", "agent")
            .prefetch_related(Prefetch("pieces_jointes", queryset=liens))
            .order_by("date_debut"),
        ),
        Prefetch(
            "affectations",
            queryset=Affectation.objects.select_related("unite", "fonction", "agent")
            .prefetch_related(Prefetch("pieces_jointes", queryset=liens))
            .order_by("date_effet"),
        ),
        Prefetch(
            "classements",
            queryset=Classement.objects.select_related("echelon__grade", "agent")
            .prefetch_related(Prefetch("pieces_jointes", queryset=liens))
            .order_by("date_effet"),
        ),
    )


def evenements_de(agent: Agent) -> list[EvenementAgent]:
    """The agent's events, newest first (D8 to D10).

    First contract: Engagement; later ones: Renouvellement de contrat. An assignment
    or classification dated on the hiring date belongs to the Engagement (kind
    None); a later assignment is a Mutation; a later classification is a Promotion
    when its grade differs from the previous row's, an Avancement d'échelon otherwise.
    """
    contrats = sorted(agent.contrats.all(), key=lambda row: row.date_debut)
    affectations = sorted(agent.affectations.all(), key=lambda row: row.date_effet)
    classements = sorted(agent.classements.all(), key=lambda row: row.date_effet)
    engagement = contrats[0].date_debut if contrats else None

    events = [
        EvenementAgent(row, "contrat", Evenement.ENGAGEMENT if i == 0 else Evenement.RENOUVELLEMENT,
                       row.date_debut)
        for i, row in enumerate(contrats)
    ]  # fmt: skip
    for row in affectations:
        kind = None if row.date_effet == engagement else Evenement.MUTATION
        events.append(EvenementAgent(row, "affectation", kind, row.date_effet))
    previous = None
    for row in classements:
        if row.date_effet == engagement or previous is None:
            kind = None
        elif row.echelon.grade_id != previous.echelon.grade_id:
            kind = Evenement.PROMOTION
        else:
            kind = Evenement.AVANCEMENT
        events.append(EvenementAgent(row, "classement", kind, row.date_effet))
        previous = row

    order = {"contrat": 0, "affectation": 1, "classement": 2}
    return sorted(events, key=lambda e: (-e.date.toordinal(), order[e.modele], -e.objet.pk))


def evenement_de(objet: Model) -> EvenementAgent:
    """The event of one row (an event model), read through its agent's history."""
    agent = prefetch_evenements(Agent.objects.filter(pk=objet.agent_id)).get()
    modele = objet._meta.model_name
    return next(e for e in evenements_de(agent) if e.modele == modele and e.objet.pk == objet.pk)
