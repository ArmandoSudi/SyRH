"""Thousands of fictional agents with their histories, to prove the agent list stays
fast at scale (agent list D18, NF-08, NF-09). Development only."""

import random
from datetime import date, timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.agents.models import Affectation, Agent, Classement, Contrat
from apps.audit import service
from apps.audit.models import EntreeAudit
from apps.referentiels.models import Echelon, Fonction, TypeContrat, UniteOrganisationnelle

NOMS = ["Mukendi", "Nsimba", "Ilunga", "Mbuyi", "Bahati", "Lokwa", "Tshibangu", "Kahindo",
        "Mavungu", "Ngalula", "Kabeya", "Kasongo", "Lumbu", "Mwamba", "Kalala", "Banza",
        "Mutombo", "Ndaya", "Kanku", "Mpiana"]  # fmt: skip
POSTNOMS = ["Kalonji", "Lukau", "Kasongo", "", "Mugisha", "Bolamba", "", "Masika", "Phambu",
            "Ntumba", "Mulumba", "Ilunga", ""]  # fmt: skip
PRENOMS_M = ["Patrick", "Jean-Pierre", "Josué", "Didier", "Olivier", "Joël", "Héritier", "Cédric"]
PRENOMS_F = ["Christine", "Esther", "Sylvie", "Grâce", "Rachel", "Aline", "Élodie", "Bénédicte"]
VILLES = ["Kinshasa", "Lubumbashi", "Goma", "Matadi", "Kananga", "Bukavu", "Mbandaka"]
LIMITE = date(2026, 12, 31)


def ouvert(row, jour: date) -> bool:
    return row.date_ouverture <= jour and (row.date_fermeture is None or jour < row.date_fermeture)


class Command(BaseCommand):
    help = (
        "Génère des agents fictifs en nombre, avec contrats, affectations et classements, "
        "pour mesurer la liste des agents. Développement uniquement : refuse de s'exécuter "
        "quand DEBUG est désactivé."
    )

    def add_arguments(self, parser):
        parser.add_argument("--nombre", type=int, default=3000)

    def handle(self, *args, nombre, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Agents de charge refusés : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )
        for command in ("create_demo_types_contrat", "create_demo_organisation",
                        "create_demo_fonctions", "create_demo_classification"):  # fmt: skip
            call_command(command, stdout=self.stdout)

        rng = random.Random(2028)
        self.unites = list(UniteOrganisationnelle.objects.all())
        self.fonctions = list(Fonction.objects.all())
        self.echelons = list(Echelon.objects.select_related("grade"))
        self.cdi = TypeContrat.objects.get(code="CDI", date_fermeture__isnull=True)
        self.cdd = TypeContrat.objects.get(code="CDD", date_fermeture__isnull=True)

        existing = set(Agent.objects.filter(matricule__startswith="CHARGE/").values_list(
            "matricule", flat=True))  # fmt: skip
        wanted = [f"CHARGE/{n:05d}" for n in range(1, nombre + 1)]
        todo = [m for m in wanted if m not in existing]
        rows: dict[type, list] = {Agent: [], Contrat: [], Affectation: [], Classement: []}

        with transaction.atomic():
            agents = [self.agent(rng, matricule) for matricule in todo]
            Agent.objects.bulk_create(agents)
            rows[Agent] = agents
            for agent in agents:
                self.histoire(rng, agent, rows)
            for model in (Contrat, Affectation, Classement):
                model.objects.bulk_create(rows[model])
            self.audit(rows)

        self.stdout.write(self.style.SUCCESS(
            f"Agents de charge prêts : {len(todo)} créés, {len(existing)} déjà présents."
        ))  # fmt: skip

    def agent(self, rng: random.Random, matricule: str) -> Agent:
        sexe = rng.choice("MF")
        return Agent(
            matricule=matricule,
            nom=rng.choice(NOMS),
            postnom=rng.choice(POSTNOMS),
            prenom=rng.choice(PRENOMS_M if sexe == "M" else PRENOMS_F),
            sexe=sexe,
            date_naissance=date(1960, 1, 1) + timedelta(days=rng.randrange(365 * 40)),
            lieu_naissance=rng.choice(VILLES),
        )

    def pick(self, rng, rows, jour):
        candidates = [row for row in rows if ouvert(row, jour)]
        return rng.choice(candidates) if candidates else None

    def histoire(self, rng: random.Random, agent: Agent, rows) -> None:
        """5 % without contract, 5 % hired in the future, 5 % on an ended CDD, the
        rest on a CDI; positions on the hiring day and one or two changes later."""
        roll = rng.random()
        if roll < 0.05:
            return
        if roll < 0.10:
            debut = date(2027, 1, 1) + timedelta(days=rng.randrange(300))
            fin = None
        elif roll < 0.15:
            debut = date(2016, 1, 1) + timedelta(days=rng.randrange(365 * 5))
            fin = debut + timedelta(days=364)
        else:
            debut = date(2015, 1, 1) + timedelta(days=rng.randrange(365 * 10))
            fin = None
        type_contrat = self.cdd if fin else self.cdi
        rows[Contrat].append(Contrat(agent=agent, type_contrat=type_contrat, date_debut=debut,
                                     date_fin=fin))  # fmt: skip
        dernier = min(fin or LIMITE, LIMITE)
        jours = [debut]
        for _ in range(rng.randrange(0, 3)):
            if (dernier - jours[-1]).days > 60:
                jours.append(
                    jours[-1] + timedelta(days=rng.randrange(30, (dernier - jours[-1]).days))
                )
        for jour in jours:
            unite = self.pick(rng, self.unites, jour)
            fonction = self.pick(rng, self.fonctions, jour)
            if unite and fonction:
                rows[Affectation].append(Affectation(agent=agent, unite=unite, fonction=fonction,
                                                     date_effet=jour))  # fmt: skip
            echelon = self.pick(rng, self.echelons, jour)
            if echelon:
                rows[Classement].append(Classement(agent=agent, echelon=echelon, date_effet=jour))

    def audit(self, rows) -> None:
        """bulk_create() skips save(): write the creation entries ourselves, in bulk."""
        entries = []
        for model, objs in rows.items():
            table = ContentType.objects.get_for_model(model)
            for obj in objs:
                entries.append(EntreeAudit(
                    action=EntreeAudit.Action.CREATION, table=table, objet_id=obj.pk,
                    objet_libelle=str(obj)[:255], module=model.module,
                    changements=service.changes(model, {}, service.snapshot(obj)),
                ))  # fmt: skip
        EntreeAudit.objects.bulk_create(entries, batch_size=2000)
