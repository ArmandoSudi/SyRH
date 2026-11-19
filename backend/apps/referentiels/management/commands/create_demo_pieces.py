from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import Evenement, PieceRequise, TypeDocument

OUVERTURE = date(2015, 1, 1)
FIN_CASIER = date(2024, 1, 1)

# code, name. A plausible list for development, not the ARPTC's real one (Q31).
TYPES = [
    ("CTR", "Contrat signé"),
    ("CNI", "Pièce d'identité"),
    ("DIP", "Diplôme"),
    ("CJ", "Extrait de casier judiciaire"),
    ("DEC", "Décision"),
    ("AMA", "Acte de mariage"),
    ("ANA", "Acte de naissance"),
    ("ADC", "Acte de décès"),
    ("JDV", "Jugement de divorce"),
    ("CRF", "Certificat de formation"),
    ("CMD", "Certificat médical"),  # for absence types, phase 5.1
]

E = Evenement
DECISION = (E.PROMOTION, E.MUTATION, E.DETACHEMENT, E.DISPONIBILITE, E.REPRISE, E.INTERIM,
            E.SANCTION, E.DISTINCTION)  # fmt: skip

# event, document code, mandatory[, opening, closing]. "Sortie" requires nothing here:
# each exit reason will carry its own document (document types D3).
PIECES = [
    (E.ENGAGEMENT, "CTR", True),
    (E.ENGAGEMENT, "CNI", True),
    (E.ENGAGEMENT, "DIP", True),
    # No longer required for hiring since 1 January 2024, with no successor.
    (E.ENGAGEMENT, "CJ", True, OUVERTURE, FIN_CASIER),
    *((evenement, "DEC", True) for evenement in DECISION),
    (E.MARIAGE, "AMA", True),
    (E.NAISSANCE, "ANA", True),
    # The cause decides which one: phase 2.14 checks it (D4).
    (E.FIN_DEPENDANCE, "ADC", False),
    (E.FIN_DEPENDANCE, "JDV", False),
    (E.FORMATION, "CRF", False),
]


class Command(BaseCommand):
    help = (
        "Charge des types de pièce et les pièces exigées par événement, pour la démonstration. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Pièces de démonstration refusées : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            types = {}
            for code, nom in TYPES:
                types[code], new = TypeDocument.objects.get_or_create(
                    code=code, date_ouverture=OUVERTURE, defaults={"nom": nom}
                )
                created += self.report(types[code], new)

            for evenement, code, obligatoire, *dates in PIECES:
                debut, fin = (*dates, None)[:2] if dates else (OUVERTURE, None)
                piece, new = PieceRequise.objects.get_or_create(
                    evenement=evenement,
                    type_document=types[code],
                    date_ouverture=debut,
                    defaults={"obligatoire": obligatoire, "date_fermeture": fin},
                )
                created += self.report(piece, new)

        done = f"Pièces de démonstration prêtes : {created} créées."
        self.stdout.write(self.style.SUCCESS(done))

    def report(self, obj, new: bool) -> int:
        if new:
            self.stdout.write(f"créé  {obj}")
        return int(new)
