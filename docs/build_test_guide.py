# ruff: noqa: E501 -- long French and English content strings
"""Builds the stakeholder test guide, docs/test-guide/syrh-test-guide.pdf.

The guide gives stakeholders the test server's address, the demo accounts with their password,
and a checklist of every feature built so far. The password is read from the local
demo-users.md, which git ignores, so the PDF is ignored too: the repository is public.

    python3 docs/build_test_guide.py

Needs reportlab and Pillow, and the Arial fonts that ship with macOS.
"""

import io
import re
from datetime import date
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "test-guide" / "syrh-test-guide.pdf"
SHOTS = ROOT / "docs" / "screenshots"
URL = "http://192.168.1.67:8080"

PASSWORD = re.search(
    r"Password \(all accounts, this machine only\):\*\* `([^`]+)`",
    (ROOT / "demo-users.md").read_text(encoding="utf-8"),
).group(1)

# Fonts: Arial for text, Arial Unicode for the check boxes.
FONTS = Path("/System/Library/Fonts/Supplemental")
pdfmetrics.registerFont(TTFont("Arial", FONTS / "Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONTS / "Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", FONTS / "Arial Italic.ttf"))
pdfmetrics.registerFont(TTFont("ArialUni", Path("/Library/Fonts/Arial Unicode.ttf")))
pdfmetrics.registerFontFamily(
    "Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-Bold"
)

# SyRH's colours (frontend/src/shared/theme/tokens.css).
INK = colors.HexColor("#14160f")
LIME = colors.HexColor("#c6f04d")
LIME_SOFT = colors.HexColor("#f1fbd2")
GREY = colors.HexColor("#5f6359")
LINE = colors.HexColor("#d9dcd2")
ROW = colors.HexColor("#f6f7f3")

S = {
    "title": ParagraphStyle("title", fontName="Arial-Bold", fontSize=26, leading=31, textColor=INK),
    "subtitle": ParagraphStyle(
        "subtitle", fontName="Arial", fontSize=13, leading=18, textColor=GREY
    ),
    "h1": ParagraphStyle(
        "h1",
        fontName="Arial-Bold",
        fontSize=17,
        leading=22,
        textColor=INK,
        spaceBefore=4,
        spaceAfter=8,
    ),
    "h2": ParagraphStyle(
        "h2",
        fontName="Arial-Bold",
        fontSize=12.5,
        leading=16,
        textColor=INK,
        spaceBefore=10,
        spaceAfter=4,
    ),
    "body": ParagraphStyle(
        "body", fontName="Arial", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=5
    ),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=8.5, leading=11.5, textColor=INK),
    "smallgrey": ParagraphStyle(
        "smallgrey", fontName="Arial", fontSize=8, leading=11, textColor=GREY
    ),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8.5, leading=11, textColor=INK),
    "cellb": ParagraphStyle(
        "cellb", fontName="Arial-Bold", fontSize=8.5, leading=11, textColor=INK
    ),
    "head": ParagraphStyle(
        "head", fontName="Arial-Bold", fontSize=8.5, leading=11, textColor=INK, alignment=TA_LEFT
    ),
    "box": ParagraphStyle("box", fontName="ArialUni", fontSize=8, leading=12, textColor=GREY),
    "bullet": ParagraphStyle(
        "bullet",
        fontName="Arial",
        fontSize=9.5,
        leading=13.5,
        textColor=INK,
        leftIndent=12,
        bulletIndent=2,
        spaceAfter=2,
    ),
}

WIDTH = A4[0] - 36 * mm


def p(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [Paragraph(item, S["bullet"], bulletText="•") for item in items]


def table(rows, widths, header=True, zebra=True):
    data = [
        [c if not isinstance(c, str) else p(c, "head" if header and i == 0 else "cell") for c in r]
        for i, r in enumerate(rows)
    ]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), LIME), ("LINEBELOW", (0, 0), (-1, 0), 0, LIME)]
    if zebra:
        start = 1 if header else 0
        for i in range(start, len(rows)):
            if (i - start) % 2 == 1:
                style.append(("BACKGROUND", (0, i), (-1, i), ROW))
    t.setStyle(TableStyle(style))
    return t


def shot(name, width=WIDTH * 0.82, crop_height=None, caption=None):
    """A screenshot, downscaled to JPEG so the PDF stays light, with a thin frame."""
    im = PILImage.open(SHOTS / f"{name}.png").convert("RGB")
    if crop_height:
        im = im.crop((0, 0, im.width, min(im.height, crop_height)))
    im.thumbnail((1400, 1400))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    buf.seek(0)
    img = Image(buf, width=width, height=width * im.height / im.width)
    framed = Table([[img]], colWidths=[width + 2])
    framed.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    parts = [framed]
    if caption:
        parts += [Spacer(1, 3), p(caption, "smallgrey")]
    return KeepTogether([Spacer(1, 4), *parts, Spacer(1, 8)])


# --- Demo accounts ---------------------------------------------------------------------------

ACCOUNTS = [
    (
        "demo.carriere",
        "Gestion de carrière",
        "Agents, Carrière, Référentiels",
        "All reference data except banks",
    ),
    (
        "demo.chef-carriere",
        "Chef de service — Gestion de carrière",
        "Agents, Carrière, Référentiels",
        "All reference data except banks",
    ),
    ("demo.personnel", "Administration du personnel", "Agents, Présences, Référentiels", "—"),
    (
        "demo.chef-personnel",
        "Chef de service — Administration du personnel",
        "Agents, Présences, Référentiels",
        "—",
    ),
    ("demo.remuneration", "Rémunération", "Agents, Paie, Référentiels", "Banks"),
    (
        "demo.chef-remuneration",
        "Chef de service — Rémunération",
        "Agents, Paie, Référentiels",
        "Banks",
    ),
    ("demo.social", "Social", "Agents, Social, Référentiels", "—"),
    ("demo.chef-social", "Chef de service — Social", "Agents, Social, Référentiels", "—"),
    ("demo.formation", "Formation", "Agents, Formation, Référentiels", "—"),
    ("demo.chef-formation", "Chef de service — Formation", "Agents, Formation, Référentiels", "—"),
    (
        "demo.direction",
        "Direction RH",
        "Agents, Carrière, Présences, Paie, Social, Formation, Référentiels, Journal d'audit",
        "—",
    ),
    (
        "demo.auditeur",
        "Auditeur",
        "Agents, Carrière, Présences, Formation, Référentiels, Journal d'audit",
        "—",
    ),
    (
        "demo.admin",
        "Administrateur système",
        "Référentiels, Journal d'audit, Système, Design",
        "All reference data; users and groups in /admin/",
    ),
]

# --- Test checklist --------------------------------------------------------------------------
# (id, account, what to do, what you should see)

SECTIONS = [
    (
        "A. Signing in and your account",
        "Any account. Changing the password is left out on purpose: the accounts are shared.",
        [
            (
                "A1",
                "demo.carriere",
                f"Open <b>{URL}</b>, type the user name and password, click <b>Se connecter</b>.",
                "The <b>Tableau de bord</b> opens; your name and profile show at the top right.",
            ),
            (
                "A2",
                "any",
                "Sign out, then sign in with a wrong password.",
                "A red message says the user name or password is wrong; the password field is "
                "cleared.",
            ),
            (
                "A3",
                "any",
                f"Signed out, open <b>{URL}/referentiels</b> directly, then sign in.",
                "After signing in you land on Référentiels, not on the dashboard.",
            ),
            (
                "A4",
                "any",
                "Click your name, then <b>Changer le mot de passe</b>. Type the current password and "
                "<b>12345678</b> twice as the new one. Click <b>Enregistrer</b>.",
                "Refused: a message under the field explains why (digits only, too common). The "
                "password is not changed.",
            ),
            (
                "A5",
                "any",
                "Click your name, then <b>Se déconnecter</b>.",
                "You are back on the <b>Connexion</b> page.",
            ),
        ],
    ),
    (
        "B. Profiles, menu and screen",
        "Sign in with several accounts from the table on page 2.",
        [
            (
                "B1",
                "each account",
                "Compare the side menu with the <i>Modules in the menu</i> column of the accounts "
                "table.",
                "Each profile sees exactly its modules; the others are not shown.",
            ),
            (
                "B2",
                "demo.social",
                f"Type <b>{URL}/paie</b> in the address bar.",
                "<b>Accès refusé</b>, with a button back to the dashboard.",
            ),
            (
                "B3",
                "any",
                "Click <b>Agents</b> (or Carrière, Paie, ...) in the menu.",
                "<b>Ce module n'est pas encore développé</b>: these modules come in later versions.",
            ),
            (
                "B4",
                "any",
                "Use the sun, moon and screen buttons in the top bar, then reload the page.",
                "Light, dark or system theme; the choice is remembered in this browser.",
            ),
            (
                "B5",
                "any",
                "Make the browser window narrow, or open SyRH on a tablet.",
                "The side menu shrinks to icons; hovering an icon shows the module's name.",
            ),
            (
                "B6",
                "any",
                "Look at the <b>Tableau de bord</b>.",
                "Example figures, marked <b>Données de démonstration</b>: not real data yet.",
            ),
        ],
    ),
    (
        "C. Reference data: reading (Référentiels)",
        "Any account: every profile can read the nine tabs. Each tab has its own date "
        "(<i>... au</i>) to see the data as it was in the past, and a search box.",
        [
            (
                "C1",
                "any",
                "<b>Organisation</b>: open units with the arrows, then <b>Tout déplier</b>. Type "
                "<i>contrôle</i> in the search box.",
                "The tree of directions, départements, services and bureaux; the search keeps the "
                "matching units and the units above them.",
            ),
            (
                "C2",
                "any",
                "<b>Organisation</b>: set the date to 15 June 2024.",
                "The Direction technique still has its <b>Service Contrôle</b>, closed on "
                "1 July 2025.",
            ),
            (
                "C3",
                "any",
                "<b>Sites</b>: turn on <b>Afficher les sites fermés</b>.",
                "The head office in Kinshasa, the provincial sites, and the closed ones once the "
                "switch is on.",
            ),
            (
                "C4",
                "any",
                "<b>Classification</b>: open <b>Attaché de 2e classe (grille 2025)</b>, then set the "
                "date to 1 June 2024.",
                "Today 5 échelons; in 2024 the older <b>Attaché de 2e classe</b>, with 3.",
            ),
            (
                "C5",
                "any",
                "<b>Fonctions</b>: search <i>ingenieur</i> (no accent), then set the date to 2023.",
                "Finds <b>Ingénieur télécoms</b>; in 2023 <b>Chargé d'études</b> is listed instead "
                "of Analyste régulation.",
            ),
            (
                "C6",
                "any",
                "<b>Types de contrat</b>: set the date to 2022.",
                "The <b>Contrat d'apprentissage</b> is listed (closed since 1 January 2023).",
            ),
            (
                "C7",
                "any",
                "<b>Pièces justificatives</b>: open <b>Engagement</b>; search <i>décision</i>; set "
                "the date to 2023.",
                "The documents each event requires, marked Obligatoire or Facultative; in 2023 hiring "
                "also required the criminal record extract.",
            ),
            (
                "C8",
                "any",
                "<b>Sorties et suspensions</b>: look at the tags, then search <i>décision</i>.",
                "Exit reasons tagged <b>Retraite</b> or <b>Décès</b>; suspension positions with their "
                "seniority rule, maximum length and renewals.",
            ),
            (
                "C9",
                "any",
                "<b>Banques</b>: set the date to 2021.",
                "<b>Union des Banques du Kasaï</b>, renamed <b>Union Bank Kivu-Kasaï</b> on "
                "1 January 2022.",
            ),
            (
                "C10",
                "any",
                "<b>Paramètres</b>: set the date to 2019.",
                "Retirement age, career length, dependants' age limit; the maximum number of children "
                "was 4 until 2020.",
            ),
        ],
    ),
    (
        "D. Reference data: changing the lists",
        "Editors only: demo.carriere (or demo.chef-carriere, demo.admin) for every list except "
        "the banks, which demo.remuneration (or demo.chef-remuneration, demo.admin) changes. "
        "Feel free to add and change rows: this is test data.",
        [
            (
                "D1",
                "demo.social",
                "Open any Référentiels tab.",
                "No <b>Ajouter</b> button and no menu at the end of the rows: readers cannot change "
                "anything.",
            ),
            (
                "D2",
                "demo.carriere",
                "<b>Fonctions</b>: <b>Ajouter</b>, fill in code, name and nature, <b>Enregistrer</b>.",
                "A confirmation message; the new fonction is in the list.",
            ),
            (
                "D3",
                "demo.carriere",
                "<b>Ajouter</b> another fonction with a code already used by an open one.",
                "Refused: the form says why at the top; nothing is saved.",
            ),
            (
                "D4",
                "demo.carriere",
                "Row menu (three dots) of a fonction, <b>Corriger</b>: fix its name.",
                "The row is changed in place, as if it had always been right.",
            ),
            (
                "D5",
                "demo.carriere",
                "Row menu, <b>Remplacer à une date</b>: a new name from a date next month.",
                "Today the old name; with the tab's date set after that date, the new name.",
            ),
            (
                "D6",
                "demo.carriere",
                "<b>Types de contrat</b>: row menu, <b>Fermer</b> from a date.",
                "After that date the type is no longer listed; before it, it still is.",
            ),
            (
                "D7",
                "demo.carriere",
                "<b>Paramètres</b>: replace the retirement age from a future date.",
                "The new value applies from that date; the old one stays visible before it.",
            ),
            (
                "D8",
                "demo.carriere, then demo.remuneration",
                "<b>Banques</b> as demo.carriere, then as demo.remuneration: add a bank with a "
                "SWIFT/BIC code.",
                "demo.carriere cannot change the banks; demo.remuneration can. A malformed SWIFT/BIC "
                "is refused.",
            ),
        ],
    ),
    (
        "E. Reference data: changing the trees",
        "demo.carriere. A <b>+</b> at the end of a row adds something under it.",
        [
            (
                "E1",
                "demo.carriere",
                "<b>Organisation</b>: <b>+</b> on a direction to add a département.",
                "The parent, the site and the type (the level below) are filled in.",
            ),
            (
                "E2",
                "demo.carriere",
                "<b>Organisation</b>: row menu of a direction, <b>Remplacer à une date</b> with a new "
                "name from next month.",
                'Before saving, the form says how many units will follow ("Les N lignes rattachées '
                'suivront") and asks to confirm. At that date the new direction has all the old '
                "one's units; today nothing has changed.",
            ),
            (
                "E3",
                "demo.carriere",
                "<b>Organisation</b>: row menu of a direction with open units, <b>Fermer</b>.",
                "Refused: the message names the units still open.",
            ),
            (
                "E4",
                "demo.carriere",
                "<b>Classification</b>: <b>+</b> on a grade.",
                "A new échelon, with the next number filled in.",
            ),
            (
                "E5",
                "demo.carriere",
                "<b>Classification</b>: replace a catégorie at a date.",
                "Its grades and échelons follow it to the new catégorie.",
            ),
            (
                "E6",
                "demo.carriere",
                "<b>Pièces justificatives</b>: <b>+</b> on an event; then add a document type in the "
                "<b>Types de pièce</b> table under the tree.",
                "The event requires the new document; the new type is listed.",
            ),
            (
                "E7",
                "demo.carriere",
                "<b>Sites</b>: open a site's row menu; try <b>Fermer</b> on a site with open units.",
                "No <b>Remplacer à une date</b> for sites; closing is refused while units on the "
                "site stay open.",
            ),
        ],
    ),
    (
        "F. Audit log and administration",
        "Do this after sections D and E, to see your own changes.",
        [
            (
                "F1",
                "demo.auditeur",
                "Open <b>Journal d'audit</b>.",
                "Every change made in D and E, newest first, with its author (Démo Gestion de "
                "carrière, ...).",
            ),
            (
                "F2",
                "demo.auditeur",
                "Filter by <b>Module</b> Référentiels, <b>Auteur</b> <i>carri</i>, <b>Action</b> and "
                "<b>Période</b>; then <b>Effacer les filtres</b>.",
                "The list narrows, with the count at the top right; clearing shows everything again.",
            ),
            (
                "F3",
                "demo.auditeur",
                "Click an entry; close the panel with Échap (Escape).",
                "<b>Détail de l'entrée</b> with each changed field, <b>Avant</b> and <b>Après</b>.",
            ),
            (
                "F4",
                "demo.carriere",
                "Look for <b>Journal d'audit</b> in the menu.",
                "Not there: only Auditeur, Direction RH and Administrateur système open it.",
            ),
            ("F5", "demo.admin", "Open <b>Système</b>.", "The API state and the database version."),
            (
                "F6",
                "demo.admin",
                f"Open <b>{URL}/admin/</b> and create an account with no profile; sign in with it in "
                "another browser.",
                "The dashboard says <b>Aucun profil ne vous est attribué</b>.",
            ),
        ],
    ),
]

NOT_YET = [
    "<b>Agents, Carrière, Présences, Paie, Social, Formation</b>: the business modules. They open "
    'a "not built yet" page; the agent record (Milestone 2) comes next.',
    "<b>Dashboard figures</b>: examples only, marked <i>Données de démonstration</i>.",
    "<b>Agent search</b> and <b>notifications</b> in the top bar: shown but not active.",
    "<b>Forgotten password</b>: no reset link; the administrator sets a new password.",
    "<b>Email</b>: SyRH sends none yet.",
    "<b>HTTPS</b>: the test server uses plain HTTP and works only on the ARPTC local network.",
]


def checklist(rows):
    data = [["#", "Account", "What to do", "What you should see", "OK?"]]
    for tid, account, todo, expected in rows:
        data.append(
            [
                p(tid, "cellb"),
                p(account, "cell"),
                p(todo, "cell"),
                p(expected, "cell"),
                p("☐ OK<br/>☐ Issue", "box"),
            ]
        )
    return table(data, [9 * mm, 26 * mm, 61 * mm, 60 * mm, 18 * mm])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(18 * mm, 10 * mm, "SyRH — Stakeholder test guide · Test data only")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(LIME)
    canvas.setLineWidth(2)
    canvas.line(18 * mm, A4[1] - 12 * mm, A4[0] - 18 * mm, A4[1] - 12 * mm)
    canvas.restoreState()


def build():
    story = []

    # Cover and how to start
    story += [
        Spacer(1, 6 * mm),
        p("SyRH", "title"),
        p("Stakeholder test guide · Milestone 1", "subtitle"),
        p(
            f"Système de gestion des ressources humaines de l'ARPTC · "
            f"{date.today().strftime('%d %B %Y')}",
            "smallgrey",
        ),
        Spacer(1, 8 * mm),
        p(
            "This guide lets you try SyRH as it stands today: signing in, the profiles and their "
            "menus, the reference data the HR modules will rely on, how the editors change it, and "
            "the audit log that records every change. Section 3 lists what to test, step by step, "
            "with what you should see."
        ),
    ]
    access = table(
        [
            ["Address", f"<b>{URL}</b>"],
            ["Network", "ARPTC local network only (office network or VPN)"],
            ["Browser", "A recent Chrome, Edge, Firefox or Safari"],
            ["Accounts", "13 demo accounts, one per profile; see section 1"],
            [
                "Data",
                "Fictional demonstration data. Add and change freely: it may be reset at any "
                "time, and nothing you do here reaches real records.",
            ],
        ],
        [28 * mm, WIDTH - 28 * mm],
        header=False,
        zebra=False,
    )
    access.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIME_SOFT),
                ("FONTNAME", (0, 0), (0, -1), "Arial-Bold"),
            ]
        )
    )
    story += [Spacer(1, 3 * mm), access, Spacer(1, 4 * mm)]
    story.append(
        shot(
            "01-login",
            width=WIDTH * 0.7,
            caption="The sign-in page. Type the user name and the password from section 1.",
        )
    )

    # 1. Accounts
    story += [
        PageBreak(),
        p("1. Demo accounts", "h1"),
        p(
            "Every account uses the same password. Sign in with the account that matches the "
            "profile you want to try; the menu, and what you may change, follow the profile."
        ),
    ]
    pw = Table(
        [
            [
                p("Password for all accounts", "cellb"),
                Paragraph(f"<font name='Courier-Bold' size='13'>{PASSWORD}</font>", S["cell"]),
            ]
        ],
        colWidths=[50 * mm, WIDTH - 50 * mm],
    )
    pw.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIME_SOFT),
                ("BOX", (0, 0), (-1, -1), 1, LIME),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story += [pw, Spacer(1, 4 * mm)]
    rows = [
        [
            "User name",
            "Password",
            "Profile",
            "Modules in the menu (plus Tableau de bord)",
            "Can change",
        ]
    ]
    for user, profile, modules, edits in ACCOUNTS:
        rows.append(
            [
                Paragraph(f"<font name='Courier-Bold' size='7.5'>{user}</font>", S["cell"]),
                Paragraph(f"<font name='Courier' size='7.5'>{PASSWORD}</font>", S["cell"]),
                profile,
                modules,
                edits,
            ]
        )
    story.append(table(rows, [40 * mm, 31 * mm, 33 * mm, 42 * mm, 28 * mm]))
    story += [
        Spacer(1, 3 * mm),
        p(
            "Salaries will be visible to Rémunération and Direction RH only, and medical "
            "details to Social and Direction RH only, once those modules exist. Please don't "
            "change these accounts' passwords: other testers share them.",
            "small",
        ),
    ]

    # 2. What SyRH does today
    story += [PageBreak(), p("2. What SyRH does today", "h1")]
    story += [p("Signing in and the account", "h2")]
    story += bullets(
        [
            "Sign-in with user name and password; a link opened before signing in is kept.",
            "Change your own password, with rules on length and strength; you are signed out "
            "everywhere else. Sign out from the account menu.",
        ]
    )
    story += [p("Profiles and navigation", "h2")]
    story += bullets(
        [
            "13 profiles of the HR department; each sees only its modules in the side menu.",
            "<b>Accès refusé</b> for a module outside the profile, even by typing its address.",
            "Light, dark and system themes; a layout for narrow screens and tablets.",
            "A dashboard previewing the figures to come (example data).",
        ]
    )
    story += [
        p("Reference data (Référentiels)", "h2"),
        p(
            "Nine tabs hold the lists the HR modules will rely on. Each keeps its history: a "
            "date field shows the list as it was on any day, and a search box filters it."
        ),
    ]
    story += bullets(
        [
            "<b>Organisation</b>: directions, départements, services and bureaux, as a tree.",
            "<b>Sites</b>: the head office and the provincial sites.",
            "<b>Classification</b>: catégories, grades and échelons.",
            "<b>Fonctions</b>: the posts, of responsibility or execution.",
            "<b>Types de contrat</b>: CDI, CDD, internship, ..., with their rules.",
            "<b>Pièces justificatives</b>: the documents each career event requires.",
            "<b>Sorties et suspensions</b>: exit reasons and suspension positions, with their rules.",
            "<b>Banques</b>: the banks agents are paid through, with their SWIFT/BIC.",
            "<b>Paramètres</b>: retirement age, career length, dependants' age and number.",
        ]
    )
    story += [p("Changing the reference data", "h2")]
    story += bullets(
        [
            "Editors add, correct, replace at a date or close rows, on every tab. Nothing is ever "
            "deleted, so the history stays readable.",
            "Replacing a parent (a direction, a catégorie, a document type) carries everything under "
            "it over to the new row, after a preview of how many rows follow.",
            "Rules are checked on saving, with the reason shown next to the field.",
            "Gestion de carrière changes the lists; Rémunération changes the banks; the system "
            "administrator changes all of them.",
        ]
    )
    story += [p("Audit and administration", "h2")]
    story += bullets(
        [
            "<b>Journal d'audit</b>: every change, with its author, date and values before and after; "
            "filters by period, author, module and action. Nobody can change it.",
            "<b>Système</b>: the application's state, for the system administrator.",
            "Administration site (<i>/admin/</i>) for the system administrator: user accounts and "
            "profiles.",
        ]
    )
    story += [p("Not available yet", "h2")]
    story += bullets(NOT_YET)

    # 3. Checklist
    story += [
        PageBreak(),
        p("3. What to test", "h1"),
        p(
            "Work through the sections in order, or pick the ones that concern you. Tick "
            "<b>OK</b> or <b>Issue</b> for each test; for an issue, note it in section 4."
        ),
    ]
    for title, intro, rows in SECTIONS:
        story += [
            CondPageBreak(45 * mm),
            p(title, "h2"),
            p(intro, "small"),
            Spacer(1, 2),
            checklist(rows),
        ]
        if title.startswith("C."):
            story.append(
                shot(
                    "08-organisation",
                    width=WIDTH * 0.75,
                    crop_height=1290,
                    caption="The Organisation tab, with its date, search box and tree.",
                )
            )
        if title.startswith("E."):
            story.append(
                shot(
                    "14u-organisation-apercu",
                    width=WIDTH * 0.75,
                    caption="Replacing a direction: the form says how many units will "
                    "follow before you save.",
                )
            )
        if title.startswith("F."):
            story.append(
                shot(
                    "19-audit-entry",
                    width=WIDTH * 0.75,
                    caption="The audit log, with the detail of one change.",
                )
            )

    # 4. Feedback
    story += [
        PageBreak(),
        p("4. Reporting an issue or a remark", "h1"),
        p("For each issue, or anything that seems wrong, unclear or missing, note:"),
    ]
    story += bullets(
        [
            "the <b>test number</b> (for example D5), or the screen if it is outside the checklist;",
            "the <b>account</b> you were signed in with;",
            "<b>what you did</b>, <b>what you saw</b>, and <b>what you expected</b>;",
            "a <b>screenshot</b> if you can.",
        ]
    )
    story += [
        p(
            "Remarks on vocabulary, the rules of the reference data (age limits, required "
            "documents, suspension rules) and the screens are as useful as bugs."
        ),
        Spacer(1, 3 * mm),
    ]
    rows = [["#", "Account", "What happened, and what you expected"]]
    rows += [["", "", ""] for _ in range(12)]
    t = table(rows, [16 * mm, 34 * mm, WIDTH - 50 * mm], zebra=False)
    t.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 26),
            ]
        )
    )
    story.append(t)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="SyRH — Stakeholder test guide",
        author="SyRH project",
        subject="Testing SyRH Milestone 1 on the test server",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
