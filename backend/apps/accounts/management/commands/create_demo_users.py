from getpass import getpass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.roles import EXTRA_PERMISSIONS, GROUPS, sync_groups


class Command(BaseCommand):
    help = (
        "Crée ou met à jour un compte de démonstration par profil (demo.<profil>). "
        "Développement uniquement : refuse de s'exécuter quand DEBUG est désactivé."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password", help="Mot de passe commun aux comptes ; demandé s'il est absent."
        )

    def handle(self, *args, password=None, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Comptes de démonstration refusés : DEBUG est désactivé. "
                "Cette commande est réservée au développement."
            )
        if not password:
            password = getpass("Mot de passe des comptes de démonstration : ")
            if password != getpass("Confirmez le mot de passe : "):
                raise CommandError("Les deux mots de passe ne correspondent pas.")
        if not password:
            raise CommandError("Le mot de passe ne peut pas être vide.")

        User = get_user_model()
        with transaction.atomic():
            sync_groups()
            for name, (slug, _) in GROUPS.items():
                user, created = User.objects.get_or_create(username=f"demo.{slug}")
                user.first_name = "Démo"
                user.last_name = name
                user.is_active = True
                # Profiles that work in Django admin (roles D9, organisation D17).
                user.is_staff = name in EXTRA_PERMISSIONS
                user.is_superuser = False
                user.set_password(password)
                user.save()
                user.groups.set([Group.objects.get(name=name)])
                verb = "créé" if created else "mis à jour"
                self.stdout.write(f"{user.username:<26} {verb:<12} {name}")

        self.stdout.write(self.style.SUCCESS(f"{len(GROUPS)} comptes de démonstration prêts."))
