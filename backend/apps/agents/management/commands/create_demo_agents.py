from datetime import date

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.agents.models import (
    Affectation,
    Agent,
    Classement,
    CompteBancaire,
    Contrat,
    Coordonnees,
)
from apps.referentiels.models import (
    Banque,
    Echelon,
    Fonction,
    Grade,
    TypeContrat,
    UniteOrganisationnelle,
)

# matricule, nom, postnom, prénom, sexe, date and place of birth[, nationality].
# Fictional agents, for development only: the real ones come with the data
# import of phase 2.15. Matricules in the payslip style (Q5).
AGENTS = [
    ("ARPTC/0001/2008", "Mukendi", "Kalonji", "Patrick", "M", date(1972, 4, 18), "Kananga"),
    ("ARPTC/0002/2008", "Nsimba", "Lukau", "Christine", "F", date(1975, 9, 2), "Matadi"),
    ("ARPTC/0003/2010", "Ilunga", "Kasongo", "Jean-Pierre", "M", date(1968, 1, 30), "Lubumbashi"),
    ("ARPTC/0004/2011", "Mbuyi", "", "Esther", "F", date(1984, 12, 11), "Mbuji-Mayi"),
    ("ARPTC/0005/2012", "Bahati", "Mugisha", "Josué", "M", date(1980, 6, 25), "Bukavu"),
    ("ARPTC/0006/2014", "Lokwa", "Bolamba", "Sylvie", "F", date(1987, 3, 8), "Mbandaka"),
    ("ARPTC/0007/2015", "Tshibangu", "", "Didier", "M", date(1979, 11, 19), "Kinshasa"),
    ("ARPTC/0008/2016", "Kahindo", "Masika", "Grâce", "F", date(1990, 7, 14), "Goma"),
    ("ARPTC/0009/2018", "Mavungu", "Phambu", "", "M", date(1964, 2, 5), "Boma"),
    ("ARPTC/0010/2020", "Ngalula", "Ntumba", "Rachel", "F", date(1993, 10, 27), "Kinshasa"),
    ("ARPTC/0011/2022", "Kabeya", "Mulumba", "Olivier", "M", date(1995, 5, 3), "Kinshasa"),
    ("ARPTC/0012/2024", "Uwimana", "", "Aline", "F", date(1996, 8, 21), "Kigali", "Rwandaise"),
]

# Fictional contact details by matricule (contact details D19): phones that
# reach nobody, emails on the reserved .example domain. Some agents have no
# second phone, no email or no emergency contact; ARPTC/0012/2024 has none.
COORDONNEES = {
    "ARPTC/0001/2008": {
        "adresse": "Avenue de la Justice 12", "commune": "Gombe", "ville": "Kinshasa",
        "telephone": "+243 81 000 0101", "telephone_secondaire": "+243 99 000 0101",
        "courriel": "p.mukendi@arptc.example",
        "urgence_nom": "Mukendi Tshiela", "urgence_lien": "Épouse",
        "urgence_telephone": "+243 81 000 0102",
    },
    "ARPTC/0002/2008": {
        "adresse": "Avenue Kasa-Vubu 40", "commune": "Kalamu", "ville": "Kinshasa",
        "telephone": "+243 82 000 0201", "courriel": "c.nsimba@arptc.example",
        "urgence_nom": "Nsimba Mbala", "urgence_lien": "Frère",
        "urgence_telephone": "+243 82 000 0202",
    },
    "ARPTC/0003/2010": {
        "adresse": "Avenue Mama Yemo 7", "commune": "Lubumbashi", "ville": "Lubumbashi",
        "telephone": "+243 97 000 0301",
        "urgence_nom": "Ilunga Mujinga", "urgence_lien": "Épouse",
        "urgence_telephone": "+243 97 000 0302",
    },
    "ARPTC/0004/2011": {
        "adresse": "Avenue Lumumba 3", "commune": "Lingwala", "ville": "Kinshasa",
        "telephone": "0810000401", "courriel": "e.mbuyi@arptc.example",
    },
    "ARPTC/0005/2012": {
        "adresse": "Avenue Patrice Lumumba 18", "commune": "Ibanda", "ville": "Bukavu",
        "telephone": "+243 99 000 0501", "telephone_secondaire": "+243 85 000 0501",
        "courriel": "j.bahati@arptc.example",
        "urgence_nom": "Bahati Neema", "urgence_lien": "Épouse",
        "urgence_telephone": "+243 99 000 0502",
    },
    "ARPTC/0006/2014": {
        "adresse": "Avenue du Fleuve 22", "commune": "Mbandaka", "ville": "Mbandaka",
        "telephone": "+243 81 000 0601", "courriel": "s.lokwa@arptc.example",
        "urgence_nom": "Lokwa Ekofo", "urgence_lien": "Père",
        "urgence_telephone": "+243 81 000 0602",
    },
    "ARPTC/0007/2015": {
        "adresse": "Avenue Bongolo 9", "commune": "Kasa-Vubu", "ville": "Kinshasa",
        "telephone": "+243 89 000 0701",
    },
    "ARPTC/0008/2016": {
        "adresse": "Avenue des Volcans 5", "commune": "Goma", "ville": "Goma",
        "telephone": "+243 97 000 0801", "courriel": "g.kahindo@arptc.example",
        "urgence_nom": "Kahindo Kavira", "urgence_lien": "Sœur",
        "urgence_telephone": "+243 97 000 0802",
    },
    "ARPTC/0009/2018": {
        "adresse": "Avenue du Port 3", "ville": "Boma",
        "telephone": "+243 85 000 0901",
        "urgence_nom": "Mavungu Nlandu", "urgence_lien": "Fils",
        "urgence_telephone": "+243 85 000 0902",
    },
    "ARPTC/0010/2020": {
        "adresse": "Avenue de la Victoire 61", "commune": "Kalamu", "ville": "Kinshasa",
        "telephone": "+243 81 000 1001", "telephone_secondaire": "+243 99 000 1001",
        "courriel": "r.ngalula@arptc.example",
        "urgence_nom": "Ngalula Kapinga", "urgence_lien": "Mère",
        "urgence_telephone": "+243 81 000 1002",
    },
    "ARPTC/0011/2022": {
        "adresse": "Boulevard du 30 Juin 150", "commune": "Gombe", "ville": "Kinshasa",
        "telephone": "+243 82 000 1101", "courriel": "o.kabeya@arptc.example",
    },
}  # fmt: skip

# Contracts by matricule (contract D20): type code, first day, last day, last day of
# probation. The demo types open on 1 January 2015 (create_demo_types_contrat), so
# agents hired earlier start there, as if their older contracts were never loaded.
# ARPTC/0012/2024 has no contract yet.
CONTRATS = {
    "ARPTC/0001/2008": [("CDI", date(2015, 1, 1), None, None)],
    "ARPTC/0002/2008": [("CDI", date(2015, 1, 1), None, None)],
    "ARPTC/0003/2010": [("CDI", date(2015, 1, 1), None, None)],
    "ARPTC/0004/2011": [("CDI", date(2015, 1, 1), None, None)],
    "ARPTC/0005/2012": [("CDI", date(2015, 1, 1), None, None)],
    # A CDD renewed once, then a CDI.
    "ARPTC/0006/2014": [
        ("CDD", date(2015, 1, 1), date(2015, 12, 31), None),
        ("CDD", date(2016, 1, 1), date(2016, 12, 31), None),
        ("CDI", date(2017, 1, 1), None, None),
    ],
    "ARPTC/0007/2015": [("CDI", date(2015, 3, 1), None, date(2015, 5, 31))],
    # A CDD with probation, renewed once, then a CDI.
    "ARPTC/0008/2016": [
        ("CDD", date(2016, 2, 1), date(2017, 1, 31), date(2016, 4, 30)),
        ("CDD", date(2017, 2, 1), date(2018, 1, 31), None),
        ("CDI", date(2018, 2, 1), None, None),
    ],
    "ARPTC/0009/2018": [("CDI", date(2018, 4, 1), None, date(2018, 6, 30))],
    "ARPTC/0010/2020": [("CDI", date(2020, 9, 1), None, date(2020, 11, 30))],
    # Still on a CDD, renewed once, running until mid-2027.
    "ARPTC/0011/2022": [
        ("CDD", date(2022, 7, 1), date(2024, 6, 30), date(2022, 9, 30)),
        ("CDD", date(2024, 7, 1), date(2027, 6, 30), None),
    ],
}  # fmt: skip

# Assignments by matricule (position history D22): effective date, unit code,
# function code, looked up among the rows open on that date. Each agent with a
# contract is placed on their hiring date; ARPTC/0012/2024 has none.
AFFECTATIONS = {
    "ARPTC/0001/2008": [(date(2015, 1, 1), "DRH", "DIR")],
    "ARPTC/0002/2008": [(date(2015, 1, 1), "DRH-CAR", "CS")],
    "ARPTC/0003/2010": [(date(2015, 1, 1), "DT", "DIR")],
    # Moved to the treasury bureau as its head.
    "ARPTC/0004/2011": [
        (date(2015, 1, 1), "DAF-FIN-CPT", "CPT"),
        (date(2021, 7, 1), "DAF-FIN-TRE", "CB"),
    ],
    # Transferred to Goma as head of service.
    "ARPTC/0005/2012": [
        (date(2015, 1, 1), "DT-TEL-FRQ", "ING"),
        (date(2019, 1, 1), "RP-NK-TEC", "CS"),
    ],
    "ARPTC/0006/2014": [(date(2015, 1, 1), "DG-SEC", "SEC")],
    "ARPTC/0007/2015": [(date(2015, 3, 1), "DRH-ADM", "ASS")],
    # The Contrôle service becomes a department on 1 July 2025; she heads it.
    "ARPTC/0008/2016": [
        (date(2016, 2, 1), "DT-CTL", "ING"),
        (date(2025, 7, 1), "DT-CTL", "CDEP"),
    ],
    "ARPTC/0009/2018": [(date(2018, 4, 1), "DAF-LOG", "CHF")],
    # "Chargé d'études" renamed "Analyste régulation" on 1 January 2024.
    "ARPTC/0010/2020": [
        (date(2020, 9, 1), "DT-POS-REG", "CE"),
        (date(2024, 1, 1), "DT-POS-REG", "CE"),
    ],
    "ARPTC/0011/2022": [(date(2022, 7, 1), "DRH-REM-PAI", "CPT")],
}

# Classifications by matricule (position history D22): effective date, grade code,
# échelon number, looked up among the rows open on that date.
CLASSEMENTS = {
    "ARPTC/0001/2008": [(date(2015, 1, 1), "DIR", 3)],
    "ARPTC/0002/2008": [(date(2015, 1, 1), "CDP", 2)],
    "ARPTC/0003/2010": [(date(2015, 1, 1), "DIR", 2)],
    "ARPTC/0004/2011": [(date(2015, 1, 1), "AT1", 2), (date(2021, 7, 1), "ATP", 1)],
    "ARPTC/0005/2012": [(date(2015, 1, 1), "AT1", 3), (date(2019, 1, 1), "ATP", 2)],
    "ARPTC/0006/2014": [(date(2015, 1, 1), "AGM", 1), (date(2020, 1, 1), "AMP", 1)],
    "ARPTC/0007/2015": [(date(2015, 3, 1), "AEP", 2)],
    # Moved to the 2025 grid of AT2, then promoted with her new post.
    "ARPTC/0008/2016": [
        (date(2016, 2, 1), "AT2", 1),
        (date(2025, 1, 1), "AT2", 2),
        (date(2025, 7, 1), "CDP", 1),
    ],
    "ARPTC/0009/2018": [(date(2018, 4, 1), "AGE", 3)],
    # A promotion already decided, effective in 2027: not current yet.
    "ARPTC/0010/2020": [(date(2020, 9, 1), "AT2", 1), (date(2027, 1, 1), "AT1", 1)],
    "ARPTC/0011/2022": [(date(2022, 7, 1), "AGM", 2)],
}


# Bank accounts by matricule (bank account D19): effective date, bank code, number,
# the bank looked up among the rows open on that date. Fictional numbers in a few
# shapes (Q36). Each agent with a contract is paid from their hiring date;
# ARPTC/0012/2024 has none.
COMPTES_BANCAIRES = {
    "ARPTC/0001/2008": [(date(2015, 1, 1), "BCF", "05100 0001001")],
    # A change of bank already announced, effective in 2027: not current yet.
    "ARPTC/0002/2008": [
        (date(2015, 1, 1), "BCF", "05100 0001002"),
        (date(2027, 1, 1), "BIK", "BIK-2027-000102"),
    ],
    # The Kasaï bank merged on 1 January 2022: a new account at its successor.
    "ARPTC/0003/2010": [
        (date(2015, 1, 1), "UBK", "UBK 0300 1003"),
        (date(2022, 1, 1), "UBK", "CD08 0003 0001 0000 0000 1003"),
    ],
    "ARPTC/0004/2011": [(date(2015, 1, 1), "CEQ", "1004-77-201500")],
    # Paid in Goma after the transfer: a change of bank.
    "ARPTC/0005/2012": [
        (date(2015, 1, 1), "BCF", "05100 0001005"),
        (date(2019, 3, 1), "CEQ", "1005-12-201903"),
    ],
    "ARPTC/0006/2014": [(date(2015, 1, 1), "TRC", "TRC0006")],
    "ARPTC/0007/2015": [(date(2015, 3, 1), "BIK", "BIK-2015-000107")],
    "ARPTC/0008/2016": [(date(2016, 2, 1), "CEQ", "1008-34-201602")],
    "ARPTC/0009/2018": [(date(2018, 4, 1), "CPM", "CPM 09 2018")],
    "ARPTC/0010/2020": [(date(2020, 9, 1), "BCF", "05100 0001010")],
    "ARPTC/0011/2022": [(date(2022, 7, 1), "BIK", "BIK-2022-000111")],
}


class Command(BaseCommand):
    help = (
        "Charge des agents fictifs, pour la démonstration. "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Agents de démonstration refusés : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )

        # Contracts, positions and bank accounts need the demo reference
        # data; these commands are idempotent.
        for command in (
            "create_demo_types_contrat",
            "create_demo_organisation",
            "create_demo_fonctions",
            "create_demo_classification",
            "create_demo_banques",
        ):
            call_command(command, stdout=self.stdout)

        created = contacts = contracts = assignments = classifications = accounts = 0
        with transaction.atomic():
            for matricule, nom, postnom, prenom, sexe, naissance, lieu, *nationalite in AGENTS:
                agent, new = Agent.objects.get_or_create(
                    matricule=matricule,
                    defaults={
                        "nom": nom,
                        "postnom": postnom,
                        "prenom": prenom,
                        "sexe": sexe,
                        "date_naissance": naissance,
                        "lieu_naissance": lieu,
                        "nationalite": nationalite[0] if nationalite else "Congolaise",
                    },
                )
                if new:
                    self.stdout.write(f"créé  {agent}")
                created += int(new)

                if matricule in COORDONNEES:
                    row, new = Coordonnees.objects.get_or_create(
                        agent=agent, defaults=COORDONNEES[matricule]
                    )
                    if new:
                        self.stdout.write(f"créé  {row}")
                    contacts += int(new)

                for code, debut, fin, essai in CONTRATS.get(matricule, []):
                    type_contrat = TypeContrat.objects.ouvertes(debut).get(code=code)
                    row, new = Contrat.objects.get_or_create(
                        agent=agent,
                        date_debut=debut,
                        defaults={
                            "type_contrat": type_contrat,
                            "date_fin": fin,
                            "fin_periode_essai": essai,
                        },
                    )
                    if new:
                        self.stdout.write(f"créé  {row}")
                    contracts += int(new)

                for jour, unite, fonction in AFFECTATIONS.get(matricule, []):
                    row, new = Affectation.objects.get_or_create(
                        agent=agent,
                        date_effet=jour,
                        defaults={
                            "unite": UniteOrganisationnelle.objects.ouvertes(jour).get(code=unite),
                            "fonction": Fonction.objects.ouvertes(jour).get(code=fonction),
                        },
                    )
                    if new:
                        self.stdout.write(f"créé  {row}")
                    assignments += int(new)

                for jour, grade, numero in CLASSEMENTS.get(matricule, []):
                    echelon = Echelon.objects.ouvertes(jour).get(
                        grade__code=grade, grade__in=Grade.objects.ouvertes(jour), numero=numero
                    )
                    row, new = Classement.objects.get_or_create(
                        agent=agent, date_effet=jour, defaults={"echelon": echelon}
                    )
                    if new:
                        self.stdout.write(f"créé  {row}")
                    classifications += int(new)
                for jour, banque, numero in COMPTES_BANCAIRES.get(matricule, []):
                    row, new = CompteBancaire.objects.get_or_create(
                        agent=agent,
                        date_effet=jour,
                        defaults={
                            "banque": Banque.objects.ouvertes(jour).get(code=banque),
                            "numero": numero,
                        },
                    )
                    if new:
                        self.stdout.write(f"créé  {row}")
                    accounts += int(new)

        done = (
            f"Agents de démonstration prêts : {created} créés, "
            f"{contacts} fiches de coordonnées créées, {contracts} contrats créés, "
            f"{assignments} affectations créées, {classifications} classements créés, "
            f"{accounts} comptes bancaires créés."
        )
        self.stdout.write(self.style.SUCCESS(done))
