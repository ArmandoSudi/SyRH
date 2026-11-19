from datetime import date

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import MotifSortie, TypeDocument, TypeSuspension

OUVERTURE = date(2015, 1, 1)

# code, name, document code, retraite, deces. Section 2.2 of the cahier des charges;
# the ARPTC's real list is Q2 and Q32.
MOTIFS = [
    ("RET-ANC", "Retraite pour ancienneté", "DRT", True, False),
    ("RET-AGE", "Retraite pour limite d'âge", "DRT", True, False),
    ("DEM", "Démission", "LDM", False, False),
    ("DCD", "Décès", "ADC", False, True),
]

# code, name, document code, counts toward seniority, maximum months, maximum renewals.
# Section 2.3; the disponibilité does not count, per the Q3 assumption.
SUSPENSIONS = [
    ("DISPO", "Mise en disponibilité", "DEC", False, 24, 1),
    ("DETA", "Détachement", "DEC", True, None, None),
]


class Command(BaseCommand):
    help = (
        "Charge des motifs de sortie et des types de suspension, pour la démonstration. "
        "Exécute d'abord create_demo_pieces. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Motifs de démonstration refusés : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        call_command("create_demo_pieces", stdout=self.stdout)
        created = 0
        with transaction.atomic():
            documents = {t.code: t for t in TypeDocument.objects.filter(date_ouverture=OUVERTURE)}

            for code, nom, document, retraite, deces in MOTIFS:
                motif, new = MotifSortie.objects.get_or_create(
                    code=code,
                    date_ouverture=OUVERTURE,
                    defaults={"nom": nom, "type_document": documents[document],
                              "retraite": retraite, "deces": deces},
                )  # fmt: skip
                created += self.report(motif, new)

            for code, nom, document, compte, duree, renouvellements in SUSPENSIONS:
                suspension, new = TypeSuspension.objects.get_or_create(
                    code=code,
                    date_ouverture=OUVERTURE,
                    defaults={"nom": nom, "type_document": documents[document],
                              "compte_anciennete": compte, "duree_max_mois": duree,
                              "renouvellements_max": renouvellements},
                )  # fmt: skip
                created += self.report(suspension, new)

        done = f"Motifs de démonstration prêts : {created} créés."
        self.stdout.write(self.style.SUCCESS(done))

    def report(self, obj, new: bool) -> int:
        if new:
            self.stdout.write(f"créé  {obj}")
        return int(new)
