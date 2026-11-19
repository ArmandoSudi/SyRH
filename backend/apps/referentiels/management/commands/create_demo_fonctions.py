from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import Fonction

OUVERTURE = date(2015, 1, 1)
RENOMMAGE = date(2024, 1, 1)

R = Fonction.Nature.RESPONSABILITE
E = Fonction.Nature.EXECUTION

# code, name, nature[, opening, closing]. Opening defaults to OUVERTURE.
# A plausible list for development, not the ARPTC's real one (Q29).
FONCTIONS = [
    ("DG", "Directeur général", R),
    ("DIR", "Directeur", R),
    ("CDEP", "Chef de département", R),
    ("CS", "Chef de service", R),
    ("CB", "Chef de bureau", R),
    ("ING", "Ingénieur télécoms", E),
    ("JUR", "Juriste", E),
    ("CPT", "Comptable", E),
    ("ASS", "Assistant administratif", E),
    ("SEC", "Secrétaire de direction", E),
    ("CHF", "Chauffeur", E),
    # Rename: "Chargé d'études" became "Analyste régulation" on 1 January 2024, same code.
    ("CE", "Chargé d'études", E, OUVERTURE, RENOMMAGE),
    ("CE", "Analyste régulation", E, RENOMMAGE),
]


class Command(BaseCommand):
    help = (
        "Charge une liste de fonctions de démonstration. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Fonctions de démonstration refusées : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            # A row is identified by its code and opening date: a successor reuses the code.
            for code, nom, nature, *dates in FONCTIONS:
                debut, fin = (*dates, None)[:2] if dates else (OUVERTURE, None)
                fonction, new = Fonction.objects.get_or_create(
                    code=code,
                    date_ouverture=debut,
                    defaults={"nom": nom, "nature": nature, "date_fermeture": fin},
                )
                if new:
                    self.stdout.write(f"créé  {fonction}")
                    created += 1

        done = f"Fonctions de démonstration prêtes : {created} créées."
        self.stdout.write(self.style.SUCCESS(done))
