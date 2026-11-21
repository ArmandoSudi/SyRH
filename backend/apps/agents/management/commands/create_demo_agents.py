from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.agents.models import Agent

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

        created = 0
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

        done = f"Agents de démonstration prêts : {created} créés."
        self.stdout.write(self.style.SUCCESS(done))
