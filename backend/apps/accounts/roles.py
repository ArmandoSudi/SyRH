"""SyRH profiles: the modules, the groups, and which group opens which module.

Single source of truth for roles (specs/2026-11-17-roles/requirements.md).
The ModuleAccess model, the group setup and HasModuleAccess all read it.
"""

# Module key -> label. Each module gets one permission, accounts.access_<key>.
MODULES: dict[str, str] = {
    "agents": "Agents",
    "carriere": "Carrière",
    "personnel": "Présences",
    "paie": "Paie",
    "social": "Social",
    "formation": "Formation",
    "referentiels": "Référentiels",
    "systeme": "Système",
    "audit": "Journal d'audit",
}

_SERVICES: dict[str, tuple[str, str]] = {
    # slug: (group name of the service, its own module)
    "carriere": ("Gestion de carrière", "carriere"),
    "personnel": ("Administration du personnel", "personnel"),
    "remuneration": ("Rémunération", "paie"),
    "social": ("Social", "social"),
    "formation": ("Formation", "formation"),
}

ADMIN_GROUP = "Administrateur système"

# Group name -> (slug for demo accounts, modules it opens). Chefs de service
# open the same modules as their service; validation rights come in phase 2.11.
GROUPS: dict[str, tuple[str, tuple[str, ...]]] = {
    **{
        name: (slug, ("agents", module, "referentiels"))
        for slug, (name, module) in _SERVICES.items()
    },
    **{
        f"Chef de service — {name}": (f"chef-{slug}", ("agents", module, "referentiels"))
        for slug, (name, module) in _SERVICES.items()
    },
    # Salaries: Rémunération and Direction RH only. Care details: Social and
    # Direction RH only, which reads every HR module (stakeholders, 2026-11-17).
    # The Auditeur reads neither pay nor care details.
    "Direction RH": (
        "direction",
        (
            "agents",
            "carriere",
            "personnel",
            "paie",
            "social",
            "formation",
            "referentiels",
            "audit",
        ),
    ),
    "Auditeur": (
        "auditeur",
        ("agents", "carriere", "personnel", "formation", "referentiels", "audit"),
    ),
    # The audit log shows each reader only the modules they open (audit phase
    # D21): for the administrator, account changes and Référentiels.
    ADMIN_GROUP: ("admin", ("referentiels", "systeme", "audit")),
}

# Django admin rights of the Administrateur système: manage accounts and
# profiles, never delete them (an account that leaves is deactivated).
ACCOUNT_ADMIN_PERMISSIONS = (
    "accounts.view_user",
    "accounts.add_user",
    "accounts.change_user",
    "auth.view_group",
    "auth.add_group",
    "auth.change_group",
)

# Editing the organisation in Django admin: sites and units, never deleted
# (organisation phase D16).
ORGANISATION_EDIT_PERMISSIONS = tuple(
    f"referentiels.{action}_{model}"
    for model in ("site", "uniteorganisationnelle")
    for action in ("view", "add", "change")
)

# Editing the classification in Django admin: catégories, grades, échelons,
# never deleted (classification phase D18, D19).
CLASSIFICATION_EDIT_PERMISSIONS = tuple(
    f"referentiels.{action}_{model}"
    for model in ("categorie", "grade", "echelon")
    for action in ("view", "add", "change")
)

# Editing the fonctions in Django admin, never deleted (fonctions phase D11, D12).
FONCTION_EDIT_PERMISSIONS = tuple(
    f"referentiels.{action}_fonction" for action in ("view", "add", "change")
)

# Editing the contract types in Django admin, never deleted (contract types D12, D13).
TYPE_CONTRAT_EDIT_PERMISSIONS = tuple(
    f"referentiels.{action}_typecontrat" for action in ("view", "add", "change")
)

# Editing the document types and the documents each event requires, never deleted
# (document types D14, D15).
DOCUMENT_EDIT_PERMISSIONS = tuple(
    f"referentiels.{action}_{model}"
    for model in ("typedocument", "piecerequise")
    for action in ("view", "add", "change")
)

# Editing the exit reasons and suspension types, never deleted (exit reasons D14, D15).
SORTIE_EDIT_PERMISSIONS = tuple(
    f"referentiels.{action}_{model}"
    for model in ("motifsortie", "typesuspension")
    for action in ("view", "add", "change")
)

# Reference data the Gestion de carrière profiles and the administrator edit.
REFERENTIELS_EDIT_PERMISSIONS = (
    ORGANISATION_EDIT_PERMISSIONS
    + CLASSIFICATION_EDIT_PERMISSIONS
    + FONCTION_EDIT_PERMISSIONS
    + TYPE_CONTRAT_EDIT_PERMISSIONS
    + DOCUMENT_EDIT_PERMISSIONS
    + SORTIE_EDIT_PERMISSIONS
)

# Group name -> Django permissions beyond module access. These groups work in
# Django admin, so their demo accounts get "Statut équipe".
EXTRA_PERMISSIONS: dict[str, tuple[str, ...]] = {
    ADMIN_GROUP: ACCOUNT_ADMIN_PERMISSIONS + REFERENTIELS_EDIT_PERMISSIONS,
    "Gestion de carrière": REFERENTIELS_EDIT_PERMISSIONS,
    "Chef de service — Gestion de carrière": REFERENTIELS_EDIT_PERMISSIONS,
}


def module_permission(module: str) -> str:
    """Full permission name for a module, as user.has_perm() expects it."""
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module!r}")
    return f"accounts.access_{module}"


def group_permissions(name: str) -> list[str]:
    _, modules = GROUPS[name]
    return [module_permission(module) for module in modules] + list(EXTRA_PERMISSIONS.get(name, ()))


def sync_groups() -> None:
    """Create missing groups and add missing permissions.

    Only ever adds: permissions granted later in Django admin are kept, so
    "configurable profiles" survive every deployment. Runs after migrate.
    What it creates or adds is written to the audit log, with no author.
    """
    from django.contrib.auth.models import Group, Permission

    from apps.audit import service
    from apps.audit.models import COMPTES

    for name in GROUPS:
        group, created = Group.objects.get_or_create(name=name)
        wanted = group_permissions(name)
        found = list(
            Permission.objects.filter(
                content_type__app_label__in={n.split(".")[0] for n in wanted}
            ).select_related("content_type")
        )
        by_name = {f"{p.content_type.app_label}.{p.codename}": p for p in found}
        missing = [n for n in wanted if n not in by_name]
        if missing:
            raise RuntimeError(f"Permissions not found for {name!r}: {missing}")

        before = service.m2m_snapshot(group, ["permissions"])
        group.permissions.add(*(by_name[n] for n in wanted))
        changes = service.m2m_changes(Group, before, service.m2m_snapshot(group, ["permissions"]))
        if created:
            changes = service.changes(Group, {}, service.snapshot(group)) + changes
        service.record(
            group,
            service.Action.CREATION if created else service.Action.MODIFICATION,
            changes,
            module=COMPTES,
        )
