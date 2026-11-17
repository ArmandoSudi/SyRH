from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.referentiels.models import Site, UniteOrganisationnelle

T = UniteOrganisationnelle.Type
OUVERTURE = date(2015, 1, 1)
RESTRUCTURATION = date(2025, 7, 1)

# code, name, city, head office
SITES = [
    ("KIN", "Siège — Kinshasa", "Kinshasa", True),
    ("LUB", "Représentation du Haut-Katanga", "Lubumbashi", False),
    ("GOM", "Représentation du Nord-Kivu", "Goma", False),
    ("KIS", "Représentation de la Tshopo", "Kisangani", False),
]

# code, name, type, parent code, site code[, opening, closing]. Parents first;
# opening defaults to OUVERTURE.
# A plausible structure for development, not the ARPTC's real organigramme (Q27).
UNITES = [
    ("DG", "Direction générale", T.DIRECTION, None, "KIN"),
    ("DG-SEC", "Secrétariat de direction", T.SERVICE, "DG", "KIN"),
    ("DRH", "Direction des Ressources humaines", T.DIRECTION, None, "KIN"),
    ("DRH-REM", "Service Rémunération", T.SERVICE, "DRH", "KIN"),
    ("DRH-REM-PAI", "Bureau Paie et déclarations", T.BUREAU, "DRH-REM", "KIN"),
    ("DRH-SOC", "Service Social", T.SERVICE, "DRH", "KIN"),
    ("DRH-ADM", "Service Administration du personnel", T.SERVICE, "DRH", "KIN"),
    ("DRH-CAR", "Service Gestion de carrière", T.SERVICE, "DRH", "KIN"),
    ("DRH-FOR", "Service Formation", T.SERVICE, "DRH", "KIN"),
    ("DT", "Direction technique", T.DIRECTION, None, "KIN"),
    ("DT-TEL", "Département Télécommunications", T.DEPARTEMENT, "DT", "KIN"),
    ("DT-TEL-FRQ", "Service Gestion des fréquences", T.SERVICE, "DT-TEL", "KIN"),
    ("DT-TEL-RES", "Service Réseaux et interconnexion", T.SERVICE, "DT-TEL", "KIN"),
    # Restructuring: the inspection service became a département on 1 July 2025.
    ("DT-CTL", "Service Contrôle", T.SERVICE, "DT-TEL", "KIN", OUVERTURE, RESTRUCTURATION),
    ("DT-CTL", "Département Contrôle et inspection", T.DEPARTEMENT, "DT", "KIN", RESTRUCTURATION),
    ("DT-POS", "Département Postes", T.DEPARTEMENT, "DT", "KIN"),
    ("DT-POS-REG", "Service Régulation postale", T.SERVICE, "DT-POS", "KIN"),
    ("DAF", "Direction administrative et financière", T.DIRECTION, None, "KIN"),
    ("DAF-FIN", "Département Finances", T.DEPARTEMENT, "DAF", "KIN"),
    ("DAF-FIN-CPT", "Service Comptabilité", T.SERVICE, "DAF-FIN", "KIN"),
    ("DAF-FIN-TRE", "Bureau Trésorerie", T.BUREAU, "DAF-FIN-CPT", "KIN"),
    ("DAF-LOG", "Service Logistique", T.SERVICE, "DAF", "KIN"),
    ("RP-HK", "Représentation provinciale du Haut-Katanga", T.DIRECTION, None, "LUB"),
    ("RP-HK-TEC", "Service technique du Haut-Katanga", T.SERVICE, "RP-HK", "LUB"),
    ("RP-HK-ADM", "Service administratif du Haut-Katanga", T.SERVICE, "RP-HK", "LUB"),
    ("RP-NK", "Représentation provinciale du Nord-Kivu", T.DIRECTION, None, "GOM"),
    ("RP-NK-TEC", "Service technique du Nord-Kivu", T.SERVICE, "RP-NK", "GOM"),
]


class Command(BaseCommand):
    help = (
        "Charge une organisation de démonstration (sites et unités). "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Organisation de démonstration refusée : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        created = 0
        with transaction.atomic():
            sites = {}
            for code, nom, ville, siege in SITES:
                sites[code], new = Site.objects.get_or_create(
                    code=code, defaults={"nom": nom, "ville": ville, "siege": siege}
                )
                created += self.report(sites[code], new)

            # A unit is identified by its code and opening date: a successor reuses the code.
            unites = {}
            for code, nom, type_, parent, site, *dates in UNITES:
                debut, fin = (*dates, None, None)[:2] if dates else (OUVERTURE, None)
                parent_unit = unites[parent] if parent else None
                unit, new = UniteOrganisationnelle.objects.get_or_create(
                    code=code,
                    date_ouverture=debut,
                    defaults={
                        "nom": nom,
                        "type": type_,
                        "parent": parent_unit,
                        "site": sites[site],
                        "date_fermeture": fin,
                    },
                )
                unites[code] = unit
                created += self.report(unit, new)

        done = f"Organisation de démonstration prête : {created} créés."
        self.stdout.write(self.style.SUCCESS(done))

    def report(self, obj, new: bool) -> int:
        if new:
            self.stdout.write(f"créé  {obj}")
        return int(new)
