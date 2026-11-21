from datetime import date

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.agents.models import Agent, Contrat, Coordonnees
from apps.referentiels.models import TypeContrat

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

        # The contracts need the demo contract types; the command is idempotent.
        call_command("create_demo_types_contrat", stdout=self.stdout)

        created = contacts = contracts = 0
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

        done = (
            f"Agents de démonstration prêts : {created} créés, "
            f"{contacts} fiches de coordonnées créées, {contracts} contrats créés."
        )
        self.stdout.write(self.style.SUCCESS(done))
