"""Reference data (roadmap milestone 1).

Organisation: sites and organisation units (specs/2026-11-18-organisation).
Classification: catégories, grades, échelons (specs/2026-11-18-classification).
Fonctions: job functions (specs/2026-11-18-fonctions).
Contract types (specs/2026-11-19-contract-types).
Document types and the documents each event requires (specs/2026-11-19-document-types).
Exit reasons and suspension types (specs/2026-11-19-exit-suspension-reasons).
Banks (specs/2026-11-19-banks).

Rules that only read the row itself are database constraints; rules that read
other rows (levels, periods, fixed fields) live in check_rules(), called by
clean() and save().
"""

import re
from datetime import date

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, F, Func, IntegerField, Q, Value, When

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


CLOSING_AFTER_OPENING = "La date de fermeture doit être postérieure à la date d'ouverture."


def check_closing_after_opening(row) -> None:
    """Refuse a closing date on or before the opening date, on the field itself.

    An error on date_fermeture makes full_clean() skip the constraints that use
    it. Without this, the exclusion constraints would build a date range ending
    before it starts, which PostgreSQL refuses with an error instead of a message.
    """
    start, end = row.date_ouverture, row.date_fermeture
    if start is not None and end is not None and end <= start:
        raise_if({"date_fermeture": [CLOSING_AFTER_OPENING]})


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
        check_closing_after_opening(self)
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


def closing_after_opening(name: str) -> models.CheckConstraint:
    """A closing date, when set, is after the opening date."""
    return models.CheckConstraint(
        condition=Q(date_fermeture__isnull=True) | Q(date_fermeture__gt=F("date_ouverture")),
        name=name,
        violation_error_message=CLOSING_AFTER_OPENING,
    )


def unique_per_period(name: str, *keys: str, message: str) -> ExclusionConstraint:
    """No two rows with the same keys over overlapping periods (classification D12)."""
    return ExclusionConstraint(
        name=name,
        expressions=[
            *((key, RangeOperators.EQUAL) for key in keys),
            (
                DateRange("date_ouverture", "date_fermeture", Value("[)")),
                RangeOperators.OVERLAPS,
            ),
        ],
        violation_error_message=message,
    )


def within_parent(row, parent, subject: str, parent_ref: str, errors: dict) -> None:
    """A row cannot open before the row it depends on, nor stay open after it
    (classification D13, document types D8, exit reasons D9)."""
    start, end = row.date_ouverture, row.date_fermeture
    if start < parent.date_ouverture:
        errors.setdefault("date_ouverture", []).append(
            f"{subject} ne peut pas ouvrir avant {parent_ref} ({fr(parent.date_ouverture)})."
        )
    if parent.date_fermeture and (end is None or end > parent.date_fermeture):
        errors.setdefault("date_fermeture", []).append(
            f"{subject} doit fermer au plus tard à la fermeture de "
            f"{parent_ref} ({fr(parent.date_fermeture)})."
        )


class ClassificationQuerySet(BaseQuerySet):
    def ouvertes(self, day: date):
        return self.filter(date_ouverture__lte=day).filter(open_on(day))


class ClassificationRules:
    """Rules shared by catégories, grades and échelons (classification D11, D13, D16).

    Each model names its parent field and its children's related name, and the
    French words its messages need. check_rules() is called by clean() (forms,
    admin) and by save() (scripts), and raises per field.
    """

    PARENT: str | None = None  # foreign key to the parent row
    CHILDREN: str | None = None  # related name of the child rows
    FIXED: tuple[str, ...] = ()  # other fields that never change after creation
    SUBJECT = ""  # "Le grade"
    PARENT_REF = ""  # "sa catégorie"
    CHILDREN_REF = ""  # "Des échelons rattachés"
    CHILDREN_OPEN = "ouverts"  # agrees with CHILDREN_REF: "ouvertes" for feminine nouns
    # Other rows that must close with this one: (related name, CHILDREN_REF, CHILDREN_OPEN).
    OTHER_CHILDREN: tuple[tuple[str, str, str], ...] = ()
    REPLACE = ""  # "fermez le grade et ouvrez-en un nouveau"

    def short_label(self) -> str:
        """How a child row is named in its parent's error messages."""
        return self.code

    def check_rules(self) -> None:
        if getattr(self, "code", None):
            self.code = self.code.strip().upper()
        check_closing_after_opening(self)
        errors: dict[str, list[str]] = {}

        fixed = ((self.PARENT,) if self.PARENT else ()) + self.FIXED
        if fixed and self.pk is not None:
            attnames = {name: self._meta.get_field(name).attname for name in fixed}
            old = type(self)._base_manager.filter(pk=self.pk).values(*attnames.values()).first()
            if old:
                raise_if(
                    {
                        name: [f"Ne peut pas être modifié : {self.REPLACE}."]
                        for name, attname in attnames.items()
                        if old[attname] != getattr(self, attname)
                    }
                )

        start, end = self.date_ouverture, self.date_fermeture
        if start is None:
            raise_if(errors)  # the required field reports itself
            return

        parent_id = getattr(self, f"{self.PARENT}_id") if self.PARENT else None
        if parent_id is not None:
            within_parent(self, getattr(self, self.PARENT), self.SUBJECT, self.PARENT_REF, errors)

        if self.pk is not None:
            children = (
                [(self.CHILDREN, self.CHILDREN_REF, self.CHILDREN_OPEN)] if self.CHILDREN else []
            )
            for related, ref, still_open in children + list(self.OTHER_CHILDREN):
                rows = getattr(self, related).all()
                if end is not None:
                    late = list(rows.filter(still_open_after(end))[:5])
                    if late:
                        names = ", ".join(c.short_label() for c in late)
                        errors.setdefault("date_fermeture", []).append(
                            f"{ref} restent {still_open} après cette date : "
                            f"{names}. Fermez-les d'abord."
                        )
                early = list(rows.filter(date_ouverture__lt=start)[:5])
                if early:
                    names = ", ".join(c.short_label() for c in early)
                    errors.setdefault("date_ouverture", []).append(
                        f"{ref} ouvrent avant cette date : {names}."
                    )

        raise_if(errors)

    def clean(self):
        super().clean()
        self.check_rules()

    def save(self, **kwargs):
        self.check_rules()
        super().save(**kwargs)


class Categorie(ClassificationRules, BaseModel):
    """A catégorie of the grid, such as Cadres de direction (classification D1, D2, D6).

    Open from date_ouverture included to date_fermeture excluded (D9). A higher
    rank is a higher position (D7).
    """

    module = "referentiels"
    CHILDREN = "grades"
    SUBJECT = "La catégorie"
    CHILDREN_REF = "Des grades rattachés"

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    rang = models.PositiveSmallIntegerField(
        "rang", help_text="Un rang plus élevé désigne une catégorie plus élevée."
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où la catégorie n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"
        ordering = ["-rang", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(rang__gt=0),
                name="categorie_rang_positif",
                violation_error_message="Le rang doit être supérieur à zéro.",
            ),
            closing_after_opening("categorie_fermeture_apres_ouverture"),
            unique_per_period(
                "categorie_code_unique_par_periode",
                "code",
                message="Une autre catégorie porte déjà ce code sur une partie de cette période.",
            ),
            unique_per_period(
                "categorie_rang_unique_par_periode",
                "rang",
                message="Une autre catégorie a déjà ce rang sur une partie de cette période.",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"


class Grade(ClassificationRules, BaseModel):
    """A grade within one catégorie (classification D1 to D3, D6, D7).

    Its catégorie never changes (D11). Its code is unique across the whole grid
    at any date (D3); its rank is unique within its catégorie (D6).
    """

    module = "referentiels"
    PARENT = "categorie"
    CHILDREN = "echelons"
    SUBJECT = "Le grade"
    PARENT_REF = "sa catégorie"
    CHILDREN_REF = "Des échelons rattachés"
    REPLACE = "fermez le grade et ouvrez-en un nouveau"

    categorie = models.ForeignKey(
        Categorie, verbose_name="catégorie", on_delete=models.PROTECT, related_name="grades"
    )
    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    rang = models.PositiveSmallIntegerField(
        "rang", help_text="Rang dans la catégorie ; un rang plus élevé désigne un grade plus élevé."
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où le grade n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "grade"
        verbose_name_plural = "grades"
        ordering = ["-categorie__rang", "-rang", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(rang__gt=0),
                name="grade_rang_positif",
                violation_error_message="Le rang doit être supérieur à zéro.",
            ),
            closing_after_opening("grade_fermeture_apres_ouverture"),
            unique_per_period(
                "grade_code_unique_par_periode",
                "code",
                message="Un autre grade porte déjà ce code sur une partie de cette période.",
            ),
            unique_per_period(
                "grade_rang_unique_par_periode",
                "categorie",
                "rang",
                message=(
                    "Un autre grade de cette catégorie a déjà ce rang "
                    "sur une partie de cette période."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"

    @property
    def cle_ordre(self) -> tuple[int, int]:
        """Sort key: a greater key is a higher grade (D7). Used by promotions (3.1)."""
        return (self.categorie.rang, self.rang)


class Echelon(ClassificationRules, BaseModel):
    """A step within one grade, known by its number (classification D1, D4, D5, D8).

    Its grade never changes (D11); it opens and closes within its grade (D10).
    """

    module = "referentiels"
    PARENT = "grade"
    SUBJECT = "L'échelon"
    PARENT_REF = "son grade"
    REPLACE = "fermez l'échelon et ouvrez-en un nouveau"

    grade = models.ForeignKey(
        Grade, verbose_name="grade", on_delete=models.PROTECT, related_name="echelons"
    )
    numero = models.PositiveSmallIntegerField("numéro")
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où l'échelon n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "échelon"
        verbose_name_plural = "échelons"
        ordering = [
            "-grade__categorie__rang",
            "-grade__rang",
            "grade__date_ouverture",
            "numero",
            "date_ouverture",
        ]
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(numero__gt=0),
                name="echelon_numero_positif",
                violation_error_message="Le numéro doit être supérieur à zéro.",
            ),
            closing_after_opening("echelon_fermeture_apres_ouverture"),
            unique_per_period(
                "echelon_numero_unique_par_periode",
                "grade",
                "numero",
                message=(
                    "Ce grade a déjà un échelon de ce numéro sur une partie de cette période."
                ),
            ),
        ]

    def __str__(self):
        grade = self.grade.code if self.grade_id else "?"
        return f"{grade} — Échelon {self.numero}"

    @property
    def libelle(self) -> str:
        return str(self)

    def short_label(self) -> str:
        return f"échelon {self.numero}"


class FlatListRules:
    """Rules of the flat, dated lists: fonctions and contract types (fonctions D9,
    contract types D10). The code is saved in capitals; a closing date on or
    before the opening date is refused on its field (fonctions D25)."""

    def __str__(self):
        return f"{self.code} — {self.nom}"

    def normalise(self) -> None:
        if self.code:
            self.code = self.code.strip().upper()

    def clean(self):
        super().clean()
        self.normalise()
        check_closing_after_opening(self)

    def save(self, **kwargs):
        self.normalise()
        super().save(**kwargs)


class Fonction(FlatListRules, BaseModel):
    """A job function, such as Chef de service or Juriste (fonctions D1, D2).

    Open from date_ouverture included to date_fermeture excluded (D5). A rename
    closes the row and opens a successor, which may keep the code (D6).
    """

    module = "referentiels"

    class Nature(models.TextChoices):
        RESPONSABILITE = "responsabilite", "Responsabilité"
        EXECUTION = "execution", "Exécution"

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    nature = models.CharField(
        "nature",
        max_length=20,
        choices=Nature.choices,
        help_text="Responsabilité : le titulaire dirige une unité ou une équipe.",
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où la fonction n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "fonction"
        verbose_name_plural = "fonctions"
        # "responsabilite" sorts after "execution": descending puts it first (D4).
        ordering = ["-nature", "nom", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(nature__in=["responsabilite", "execution"]),
                name="fonction_nature_valide",
                violation_error_message="Nature inconnue.",
            ),
            closing_after_opening("fonction_fermeture_apres_ouverture"),
            unique_per_period(
                "fonction_code_unique_par_periode",
                "code",
                message="Une autre fonction porte déjà ce code sur une partie de cette période.",
            ),
        ]


class TypeContrat(FlatListRules, BaseModel):
    """A contract type, such as CDI or Stage (contract types D1, D2).

    The two flags tell phase 2.3 whether a contract of this type must have an end
    date and whether it may have a probation period. Open from date_ouverture
    included to date_fermeture excluded (D6); changing a flag closes the type and
    opens a successor (D7).
    """

    module = "referentiels"

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    duree_determinee = models.BooleanField(
        "durée déterminée", help_text="Un contrat de ce type doit avoir une date de fin."
    )
    periode_essai = models.BooleanField(
        "période d'essai",
        help_text="Un contrat de ce type peut comporter une période d'essai.",
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où le type n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "type de contrat"
        verbose_name_plural = "types de contrat"
        ordering = ["nom", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            closing_after_opening("typecontrat_fermeture_apres_ouverture"),
            unique_per_period(
                "typecontrat_code_unique_par_periode",
                "code",
                message=(
                    "Un autre type de contrat porte déjà ce code sur une partie de cette période."
                ),
            ),
        ]


class TypeDocument(ClassificationRules, BaseModel):
    """A kind of supporting document, such as Acte de naissance (document types D1).

    Open from date_ouverture included to date_fermeture excluded (D7). Its
    requirements stay within its period (D8).
    """

    module = "referentiels"
    CHILDREN = "pieces_requises"
    SUBJECT = "Le type de pièce"
    CHILDREN_REF = "Des pièces exigées"
    CHILDREN_OPEN = "ouvertes"
    OTHER_CHILDREN = (
        ("motifs_sortie", "Des motifs de sortie", "ouverts"),
        ("types_suspension", "Des types de suspension", "ouverts"),
    )

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où le type n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "type de pièce"
        verbose_name_plural = "types de pièce"
        ordering = ["nom", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            closing_after_opening("typedocument_fermeture_apres_ouverture"),
            unique_per_period(
                "typedocument_code_unique_par_periode",
                "code",
                message=(
                    "Un autre type de pièce porte déjà ce code sur une partie de cette période."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.nom}"


class Evenement(models.TextChoices):
    """Event kinds that rest on a document, in the order of the agent's life (document
    types D2). The screen lists them in this order; the frontend mirrors this list."""

    ENGAGEMENT = "engagement", "Engagement"
    PROMOTION = "promotion", "Promotion"
    MUTATION = "mutation", "Mutation ou changement de fonction"
    DETACHEMENT = "detachement", "Détachement"
    DISPONIBILITE = "disponibilite", "Mise en disponibilité"
    REPRISE = "reprise", "Reprise de service"
    INTERIM = "interim", "Intérim"
    SANCTION = "sanction", "Sanction"
    DISTINCTION = "distinction", "Distinction"
    SORTIE = "sortie", "Sortie"
    MARIAGE = "mariage", "Mariage"
    NAISSANCE = "naissance", "Naissance"
    FIN_DEPENDANCE = "fin_dependance", "Fin de qualité de dépendant"
    FORMATION = "formation", "Formation"


class PieceRequise(ClassificationRules, BaseModel):
    """A document type an event kind requires, mandatory or optional (document types
    D1 to D4).

    The event kinds are fixed in code (D2); which documents each needs is data. A
    requirement lies within its type's period (D8); its event and type never change
    (D9).
    """

    module = "referentiels"
    PARENT = "type_document"
    FIXED = ("evenement",)
    SUBJECT = "La pièce exigée"
    PARENT_REF = "son type de pièce"
    REPLACE = "fermez la pièce exigée et ouvrez-en une nouvelle"

    Evenement = Evenement

    evenement = models.CharField("événement", max_length=20, choices=Evenement.choices)
    type_document = models.ForeignKey(
        TypeDocument,
        verbose_name="type de pièce",
        on_delete=models.PROTECT,
        related_name="pieces_requises",
    )
    obligatoire = models.BooleanField(
        "obligatoire",
        help_text="Une pièce obligatoire manquante bloque la validation de l'événement.",
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où la pièce n'est plus exigée.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "pièce exigée"
        verbose_name_plural = "pièces exigées"
        # The event in the order of D2, mandatory first, then the document's name (D6).
        ordering = [
            Case(
                *(
                    When(evenement=value, then=Value(position))
                    for position, value in enumerate(Evenement.values)
                ),
                output_field=IntegerField(),
            ),
            "-obligatoire",
            "type_document__nom",
            "date_ouverture",
        ]
        default_permissions = NO_DELETE
        constraints = [
            models.CheckConstraint(
                condition=Q(evenement__in=Evenement.values),
                name="piecerequise_evenement_valide",
                violation_error_message="Événement inconnu.",
            ),
            closing_after_opening("piecerequise_fermeture_apres_ouverture"),
            unique_per_period(
                "piecerequise_unique_par_periode",
                "evenement",
                "type_document",
                message=(
                    "Cet événement exige déjà ce type de pièce sur une partie de cette période."
                ),
            ),
        ]

    def __str__(self):
        code = self.type_document.code if self.type_document_id else "?"
        nature = "obligatoire" if self.obligatoire else "facultative"
        return f"{self.get_evenement_display()} — {code} ({nature})"

    def short_label(self) -> str:
        return self.get_evenement_display().lower()


RETRAITE_ET_DECES = "Un motif ne peut pas être à la fois une retraite et un décès."


DUREE_NULLE = (
    "La durée maximale doit être d'au moins un mois ; laissez vide si la décision la fixe."
)


class DocumentRules(FlatListRules):
    """Flat lists whose rows rest on a document type: exit reasons and suspension
    types (exit reasons D9, D12). A row stays within its document type's period."""

    SUBJECT = ""  # "Le motif de sortie"

    def short_label(self) -> str:
        return self.code

    def check_document(self) -> None:
        if self.date_ouverture is None or self.type_document_id is None:
            return  # the required fields report themselves
        errors: dict[str, list[str]] = {}
        within_parent(self, self.type_document, self.SUBJECT, "son type de pièce", errors)
        raise_if(errors)

    def clean(self):
        super().clean()
        self.check_document()

    def save(self, **kwargs):
        check_closing_after_opening(self)
        self.check_document()
        super().save(**kwargs)


class MotifSortie(DocumentRules, BaseModel):
    """Why an agent leaves for good, such as Démission (exit reasons D1, D2, D4).

    Phase 3.6 records an exit with one of these reasons and requires its document;
    the flags tell later phases which reasons are retirements and deaths. A reason
    whose rules change is closed and a successor opened (D8).
    """

    module = "referentiels"
    SUBJECT = "Le motif de sortie"

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    type_document = models.ForeignKey(
        TypeDocument,
        verbose_name="pièce exigée",
        on_delete=models.PROTECT,
        related_name="motifs_sortie",
        help_text="La pièce sur laquelle repose la sortie.",
    )
    retraite = models.BooleanField(
        "retraite",
        default=False,
        help_text="Compté dans les prévisions et alertes de départ à la retraite.",
    )
    deces = models.BooleanField(
        "décès",
        default=False,
        help_text="La sortie profite aux ayants droit, identifiés parmi les dépendants.",
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où le motif n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "motif de sortie"
        verbose_name_plural = "motifs de sortie"
        ordering = ["nom", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            closing_after_opening("motifsortie_fermeture_apres_ouverture"),
            unique_per_period(
                "motifsortie_code_unique_par_periode",
                "code",
                message=(
                    "Un autre motif de sortie porte déjà ce code sur une partie de cette période."
                ),
            ),
            models.CheckConstraint(
                condition=~Q(retraite=True, deces=True),
                name="motifsortie_retraite_ou_deces",
                violation_error_message=RETRAITE_ET_DECES,
            ),
        ]

    def clean(self):
        if self.retraite and self.deces:
            raise ValidationError({"deces": [RETRAITE_ET_DECES]})
        super().clean()


class TypeSuspension(DocumentRules, BaseModel):
    """A position that suspends a career without ending it, such as Détachement
    (exit reasons D1, D3, D4).

    Phase 3.4 records suspensions of this type, enforcing the maximum length and
    renewals; phase 3.5 counts their periods toward seniority when the flag is on.
    A type whose rules change is closed and a successor opened (D8).
    """

    module = "referentiels"
    SUBJECT = "Le type de suspension"

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    type_document = models.ForeignKey(
        TypeDocument,
        verbose_name="pièce exigée",
        on_delete=models.PROTECT,
        related_name="types_suspension",
        help_text="La pièce sur laquelle repose la suspension.",
    )
    compte_anciennete = models.BooleanField(
        "compte dans l'ancienneté",
        help_text="La période compte dans l'ancienneté et dans les 30 ans de carrière.",
    )
    duree_max_mois = models.PositiveSmallIntegerField(
        "durée maximale (mois)",
        null=True,
        blank=True,
        help_text="Durée la plus longue d'une période. Vide : fixée par la décision.",
    )
    renouvellements_max = models.PositiveSmallIntegerField(
        "renouvellements maximum",
        null=True,
        blank=True,
        help_text="Nombre de renouvellements permis. Vide : sans limite.",
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où le type n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "type de suspension"
        verbose_name_plural = "types de suspension"
        ordering = ["nom", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            closing_after_opening("typesuspension_fermeture_apres_ouverture"),
            unique_per_period(
                "typesuspension_code_unique_par_periode",
                "code",
                message=(
                    "Un autre type de suspension porte déjà ce code sur une partie de cette "
                    "période."
                ),
            ),
            models.CheckConstraint(
                condition=Q(duree_max_mois__isnull=True) | Q(duree_max_mois__gt=0),
                name="typesuspension_duree_positive",
                violation_error_message=DUREE_NULLE,
            ),
            models.CheckConstraint(
                condition=Q(renouvellements_max__isnull=True) | Q(renouvellements_max__gte=0),
                name="typesuspension_renouvellements_positifs",
                violation_error_message="Le nombre de renouvellements ne peut pas être négatif.",
            ),
        ]

    def clean(self):
        if self.duree_max_mois == 0:
            raise ValidationError({"duree_max_mois": [DUREE_NULLE]})
        super().clean()


SWIFT_PATTERN = r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$"
SWIFT_INVALIDE = (
    "Code SWIFT/BIC invalide : 8 ou 11 caractères, soit 4 lettres pour la banque, 2 pour le "
    "pays, 2 lettres ou chiffres pour la ville, et éventuellement 3 pour l'agence."
)


class Banque(FlatListRules, BaseModel):
    """A bank agents are paid through, such as one of Kinshasa's commercial banks (banks D1, D2).

    Phase 2.5 attaches each agent's account to one of these; the transfer file
    template waits for Q16 (D3). A renamed or merged bank is closed and a
    successor opened (D7).
    """

    module = "referentiels"

    code = models.CharField("code", max_length=20)
    nom = models.CharField("nom", max_length=150)
    swift = models.CharField(
        "code SWIFT/BIC",
        max_length=11,
        blank=True,
        help_text="8 ou 11 caractères, par exemple ABCDCDKI. Facultatif.",
    )
    date_ouverture = models.DateField("date d'ouverture")
    date_fermeture = models.DateField(
        "date de fermeture",
        null=True,
        blank=True,
        help_text="Premier jour où la banque n'existe plus.",
    )

    objects = ClassificationQuerySet.as_manager()

    class Meta:
        verbose_name = "banque"
        verbose_name_plural = "banques"
        ordering = ["nom", "date_ouverture"]
        default_permissions = NO_DELETE
        constraints = [
            closing_after_opening("banque_fermeture_apres_ouverture"),
            unique_per_period(
                "banque_code_unique_par_periode",
                "code",
                message="Une autre banque porte déjà ce code sur une partie de cette période.",
            ),
            models.CheckConstraint(
                condition=Q(swift="") | Q(swift__regex=SWIFT_PATTERN),
                name="banque_swift_valide",
                violation_error_message=SWIFT_INVALIDE,
            ),
        ]

    def normalise(self) -> None:
        super().normalise()
        self.swift = (self.swift or "").strip().upper()

    def clean(self):
        super().clean()
        if self.swift and not re.fullmatch(SWIFT_PATTERN, self.swift):
            raise ValidationError({"swift": [SWIFT_INVALIDE]})
