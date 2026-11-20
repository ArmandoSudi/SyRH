from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import Cle, Parametre

OUVERTURE = date(2015, 1, 1)
CHANGEMENT = date(2020, 1, 1)

# key, value[, opening, closing]. The age limit, retirement age and career length are
# the cahier des charges' values; the maximum number of children is fictional (Q34).
PARAMETRES = [
    (Cle.AGE_LIMITE_ENFANT, 25),
    (Cle.ENFANTS_MAX, 4, OUVERTURE, CHANGEMENT),
    (Cle.ENFANTS_MAX, 6, CHANGEMENT, None),
    (Cle.AGE_RETRAITE, 65),
    (Cle.DUREE_CARRIERE, 30),
]


class Command(BaseCommand):
    help = (
        "Charge les paramètres généraux de démonstration. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Paramètres de démonstration refusés : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            for cle, valeur, *dates in PARAMETRES:
                debut, fin = dates if dates else (OUVERTURE, None)
                row, new = Parametre.objects.get_or_create(
                    cle=cle,
                    date_ouverture=debut,
                    defaults={"valeur": valeur, "date_fermeture": fin},
                )
                if new:
                    self.stdout.write(f"créé  {row}")
                created += int(new)

        done = f"Paramètres de démonstration prêts : {created} créés."
        self.stdout.write(self.style.SUCCESS(done))
