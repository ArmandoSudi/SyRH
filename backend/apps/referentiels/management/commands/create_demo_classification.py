from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import Categorie, Echelon, Grade

OUVERTURE = date(2015, 1, 1)
REFORME = date(2025, 1, 1)

# code, name, rank (a higher rank is a higher catégorie).
# A plausible grid for development, not the ARPTC's real one (Q28).
CATEGORIES = [
    ("CD", "Cadres de direction", 4),
    ("CC", "Cadres de collaboration", 3),
    ("AM", "Agents de maîtrise", 2),
    ("AE", "Agents d'exécution", 1),
]

# code, name, catégorie code, rank in the catégorie, number of échelons[, opening, closing].
# Opening defaults to OUVERTURE; the échelons open and close with their grade.
GRADES = [
    ("DIR", "Directeur", "CD", 2, 3),
    ("CDP", "Chef de département", "CD", 1, 4),
    ("ATP", "Attaché principal", "CC", 3, 5),
    ("AT1", "Attaché de 1re classe", "CC", 2, 5),
    # Reform: the Attaché de 2e classe grade got a longer scale on 1 January 2025.
    ("AT2", "Attaché de 2e classe", "CC", 1, 3, OUVERTURE, REFORME),
    ("AT2", "Attaché de 2e classe (grille 2025)", "CC", 1, 5, REFORME),
    ("AMP", "Agent de maîtrise principal", "AM", 2, 4),
    ("AGM", "Agent de maîtrise", "AM", 1, 4),
    ("AEP", "Agent d'exécution principal", "AE", 2, 4),
    ("AGE", "Agent d'exécution", "AE", 1, 3),
]


class Command(BaseCommand):
    help = (
        "Charge une classification de démonstration (catégories, grades, échelons). "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Classification de démonstration refusée : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            # A row is identified by its code and opening date: a successor reuses the code.
            categories = {}
            for code, nom, rang in CATEGORIES:
                categories[code], new = Categorie.objects.get_or_create(
                    code=code, date_ouverture=OUVERTURE, defaults={"nom": nom, "rang": rang}
                )
                created += self.report(categories[code], new)

            for code, nom, categorie, rang, echelons, *dates in GRADES:
                debut, fin = (*dates, None)[:2] if dates else (OUVERTURE, None)
                grade, new = Grade.objects.get_or_create(
                    code=code,
                    date_ouverture=debut,
                    defaults={
                        "nom": nom,
                        "categorie": categories[categorie],
                        "rang": rang,
                        "date_fermeture": fin,
                    },
                )
                created += self.report(grade, new)
                for numero in range(1, echelons + 1):
                    step, new = Echelon.objects.get_or_create(
                        grade=grade,
                        numero=numero,
                        defaults={"date_ouverture": debut, "date_fermeture": fin},
                    )
                    created += self.report(step, new)

        done = f"Classification de démonstration prête : {created} créés."
        self.stdout.write(self.style.SUCCESS(done))

    def report(self, obj, new: bool) -> int:
        if new:
            self.stdout.write(f"créé  {obj}")
        return int(new)
