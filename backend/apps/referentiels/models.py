"""Reference data (roadmap milestone 1). Organisation: sites and organisation units.

See specs/2026-11-18-organisation/requirements.md. Rules that only read the
row itself are database constraints; rules that read other rows (levels,
periods, fixed fields) live in check_rules(), called by clean() and save().
"""

from datetime import date

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, Q, Value

from apps.core.models import BaseModel, BaseQuerySet

NO_DELETE = ("view", "add", "change")  # nothing is deleted: rows are closed (D12)


def fr(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def open_on(day: date) -> Q:
    """Rows open on a day: the closing date is the first day closed (D7)."""
    return Q(date_fermeture__isnull=True) | Q(date_fermeture__gt=day)


def still_open_after(day: date | None) -> Q:
    """Rows that stay open after a closing day (all rows when day is None)."""
    if day is None:
        return Q()
    return Q(date_fermeture__isnull=True) | Q(date_fermeture__gt=day)


def raise_if(errors: dict[str, list[str]]) -> None:
    if errors:
        raise ValidationError(errors)


class SiteQuerySet(BaseQuerySet):
    def ouverts(self, day: date):
        return self.filter(open_on(day))


class Site(BaseModel):
    """An ARPTC site: the head office or a provincial representation (D5, D6)."""

    module = "referentiels"

    code = models.CharField("code", max_length=20, unique=True)
    nom = models.CharField("nom", max_length=150)
    ville = models.CharField("ville", max_length=100)
    siege = models.BooleanField("siège", default=False)
    date_fermeture = models.DateField("date de fermeture", null=True, blank=True)

    objects = SiteQuerySet.as_manager()

    class Meta:
        verbose_name = "site"
        verbose_name_plural = "sites"
        ordering = ["-siege", "code"]
        default_permissions = NO_DELETE
        constraints = [
            models.UniqueConstraint(
                fields=["siege"],
                condition=Q(siege=True, date_fermeture__isnull=True),
                name="site_un_seul_siege_ouvert",
                violation_error_message="Un autre site ouvert est déjà le siège.",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"

    def check_rules(self) -> None:
        """A site cannot close while a unit located there stays open (D11)."""
        if self.code:
            self.code = self.code.strip().upper()
        if self.pk is None or self.date_fermeture is None:
            return
        open_units = self.unites.filter(still_open_after(self.date_fermeture))
        if open_units.exists():
            names = ", ".join(u.code for u in open_units[:5])
            raise_if(
                {
                    "date_fermeture": [
                        "Des unités de ce site restent ouvertes après cette date : "
                        f"{names}. Fermez-les d'abord."
                    ]
                }
            )

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)


class DateRange(Func):
    function = "daterange"
    output_field = DateRangeField()


class UniteQuerySet(BaseQuerySet):
    def ouvertes(self, day: date):
        return self.filter(date_ouverture__lte=day).filter(open_on(day))


class UniteOrganisationnelle(BaseModel):
    """A direction, département, service or bureau, in a tree (D1 to D4).

    Type, parent and site never change: a restructuring closes the unit and
    opens new ones (D8). A unit is open from date_ouverture included to
    date_fermeture excluded (D7).
    """

    module = "referentiels"

    class Type(models.TextChoices):
        DIRECTION = "direction", "Direction"
        DEPARTEMENT = "departement", "Département"
        SERVICE = "service", "Service"
        BUREAU = "bureau", "Bureau"

    # Level of each type: a parent's level is strictly lower (D2).
    NIVEAUX = {Type.DIRECTION: 1, Type.DEPARTEMENT: 2, Type.SERVICE: 3, Type.BUREAU: 4}
    FIXED = ("type", "parent", "site")
    ARTICLES = {
        Type.DIRECTION: "une direction",
        Type.DEPARTEMENT: "un département",
        Type.SERVICE: "un service",
        Type.BUREAU: "un bureau",
    }

    type = models.CharField("type", max_length=20, choices=Type.choices)
    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    parent = models.ForeignKey(
        "self",
        verbose_name="unité parente",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enfants",
    )
    site = models.ForeignKey(
        Site, verbose_name="site", on_delete=models.PROTECT, related_name="unites"
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où l'unité n'existe plus.",
    )

    objects = UniteQuerySet.as_manager()

    class Meta:
        verbose_name = "unité organisationnelle"
        verbose_name_plural = "unités organisationnelles"
        ordering = ["code", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(type="direction", parent__isnull=True)
                | (~Q(type="direction") & Q(parent__isnull=False)),
                name="unite_racine_si_direction",
                violation_error_message=(
                    "Une direction n'a pas d'unité parente ; toute autre unité en a une."
                ),
            ),
            models.CheckConstraint(
                condition=~Q(parent=F("id")),
                name="unite_pas_son_propre_parent",
                violation_error_message="Une unité ne peut pas être sa propre parente.",
            ),
            models.CheckConstraint(
                condition=Q(date_fermeture__isnull=True)
                | Q(date_fermeture__gt=F("date_ouverture")),
                name="unite_fermeture_apres_ouverture",
                violation_error_message=(
                    "La date de fermeture doit être postérieure à la date d'ouverture."
                ),
            ),
            ExclusionConstraint(
                name="unite_code_unique_par_periode",
                expressions=[
                    ("code", RangeOperators.EQUAL),
                    (
                        DateRange("date_ouverture", "date_fermeture", Value("[)")),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                violation_error_message=(
                    "Une autre unité porte déjà ce code sur une partie de cette période."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"

    @property
    def niveau(self) -> int:
        return self.NIVEAUX[self.type]

    def check_rules(self) -> None:
        """Rules that read other rows (D2, D8, D10, D11). Raises per field, in French."""
        if self.code:
            self.code = self.code.strip().upper()
        errors: dict[str, list[str]] = {}

        old = None
        if self.pk is not None:
            old = type(self)._base_manager.filter(pk=self.pk).first()
        if old is not None:
            for name in self.FIXED:
                attname = self._meta.get_field(name).attname
                if getattr(old, attname) != getattr(self, attname):
                    errors.setdefault(name, []).append(
                        "Ne peut pas être modifié : fermez l'unité et ouvrez-en une nouvelle."
                    )
            raise_if(errors)

        start, end = self.date_ouverture, self.date_fermeture

        if self.parent_id is not None and self.type in self.NIVEAUX:
            parent = self.parent
            if parent.niveau >= self.niveau:
                errors.setdefault("parent", []).append(
                    f"{self.ARTICLES[self.type].capitalize()} ne peut pas relever "
                    f"d'{self.ARTICLES[parent.type]} : l'unité parente doit être "
                    "d'un niveau supérieur."
                )
            if start and start < parent.date_ouverture:
                errors.setdefault("date_ouverture", []).append(
                    "L'unité ne peut pas ouvrir avant son unité parente "
                    f"({fr(parent.date_ouverture)})."
                )
            if start and parent.date_fermeture and (end is None or end > parent.date_fermeture):
                errors.setdefault("date_fermeture", []).append(
                    "L'unité doit fermer au plus tard à la fermeture de son unité parente "
                    f"({fr(parent.date_fermeture)})."
                )

        if self.site_id is not None and self.site.date_fermeture is not None:
            closed = self.site.date_fermeture
            if end is None or end > closed:
                errors.setdefault("site", []).append(
                    f"Ce site ferme le {fr(closed)} : "
                    "l'unité doit fermer au plus tard à cette date."
                )

        if self.pk is not None and start:
            children = self.enfants.all()
            late = children.filter(still_open_after(end)) if end else None
            if late is not None and late.exists():
                names = ", ".join(u.code for u in late[:5])
                errors.setdefault("date_fermeture", []).append(
                    f"Des unités rattachées restent ouvertes après cette date : {names}. "
                    "Fermez-les d'abord."
                )
            early = children.filter(date_ouverture__lt=start)
            if early.exists():
                names = ", ".join(u.code for u in early[:5])
                errors.setdefault("date_ouverture", []).append(
                    f"Des unités rattachées ouvrent avant cette date : {names}."
                )

        raise_if(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)
