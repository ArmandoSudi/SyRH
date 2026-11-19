from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import TypeContrat

OUVERTURE = date(2015, 1, 1)
RETRAIT = date(2023, 1, 1)

# code, name, durée déterminée, période d'essai[, opening, closing].
# The four types of section 4.1 of the cahier des charges, with plausible rules for
# development; the ARPTC's real list and rules are open question Q30.
TYPES = [
    ("CDI", "Contrat à durée indéterminée", False, True),
    ("CDD", "Contrat à durée déterminée", True, True),
    ("STG", "Stage", True, False),
    ("JRN", "Journalier", False, False),
    # Retired with no successor: no apprenticeship contract since 1 January 2023.
    ("APP", "Contrat d'apprentissage", True, False, OUVERTURE, RETRAIT),
]


class Command(BaseCommand):
    help = (
        "Charge des types de contrat de démonstration. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Types de contrat de démonstration refusés : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            # A row is identified by its code and opening date: a successor reuses the code.
            for code, nom, fixe, essai, *dates in TYPES:
                debut, fin = (*dates, None)[:2] if dates else (OUVERTURE, None)
                type_contrat, new = TypeContrat.objects.get_or_create(
                    code=code,
                    date_ouverture=debut,
                    defaults={
                        "nom": nom,
                        "duree_determinee": fixe,
                        "periode_essai": essai,
                        "date_fermeture": fin,
                    },
                )
                if new:
                    self.stdout.write(f"créé  {type_contrat}")
                    created += 1

        done = f"Types de contrat de démonstration prêts : {created} créés."
        self.stdout.write(self.style.SUCCESS(done))
