from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import Banque

OUVERTURE = date(2015, 1, 1)
FUSION = date(2022, 1, 1)

# code, name, SWIFT/BIC[, opening, closing]. Fictional banks with fictional codes, for
# development only: the ARPTC's real list is Q33.
BANQUES = [
    ("BCF", "Banque Commerciale du Fleuve", "BCFLCDKI"),
    ("CEQ", "Crédit de l'Équateur", "CEQUCDKIXXX"),
    ("BIK", "Banque Internationale de Kinshasa", "BIKICDKI"),
    ("TRC", "Trésor Crédit", ""),  # no SWIFT/BIC recorded
    ("CPM", "Caisse Populaire du Mayombe", "CPMACDKI"),
    # Merged with a Kivu bank on 1 January 2022: same code, new name and SWIFT/BIC.
    ("UBK", "Union des Banques du Kasaï", "UBKACDKA", OUVERTURE, FUSION),
    ("UBK", "Union Bank Kivu-Kasaï", "UBKKCDKI", FUSION, None),
]


class Command(BaseCommand):
    help = (
        "Charge des banques fictives, pour la démonstration. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Banques de démonstration refusées : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            for code, nom, swift, *dates in BANQUES:
                debut, fin = dates if dates else (OUVERTURE, None)
                banque, new = Banque.objects.get_or_create(
                    code=code,
                    date_ouverture=debut,
                    defaults={"nom": nom, "swift": swift, "date_fermeture": fin},
                )
                if new:
                    self.stdout.write(f"créé  {banque}")
                created += int(new)

        done = f"Banques de démonstration prêtes : {created} créées."
        self.stdout.write(self.style.SUCCESS(done))
