"""Retake the screenshots of docs/user-guide.md.

Needs both dev servers running (backend on 8000, frontend on 5173), the demo data
(create_demo_users, create_demo_organisation, create_demo_classification,
create_demo_fonctions, create_demo_types_contrat, create_demo_pieces, create_demo_sorties,
create_demo_banques) and Google Chrome.
From the repository root:

    uv run --no-project --with playwright python docs/capture_screenshots.py

Pass screenshot names (without .png) to retake only those, e.g. `... 05-password 12-sites`.
The demo password is read from demo-users.md.
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "screenshots"
BASE = "http://localhost:5173"
PASSWORD = re.search(r"`(Demo-[^`]+)`", (REPO / "demo-users.md").read_text()).group(1)

OUT.mkdir(parents=True, exist_ok=True)
only = set(sys.argv[1:])


def shot(page: Page, name: str, full_page: bool = False, **kw) -> None:
    if only and name not in only:
        return
    page.wait_for_timeout(400)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full_page, **kw)
    print("saved", name)


def tall(page: Page, name: str) -> None:
    if only and name not in only:
        return
    page.wait_for_timeout(400)
    size = page.viewport_size
    height = page.evaluate("document.documentElement.scrollHeight")
    page.set_viewport_size({"width": size["width"], "height": max(height, size["height"])})
    page.wait_for_timeout(300)
    height = page.evaluate("document.documentElement.scrollHeight")
    page.set_viewport_size({"width": size["width"], "height": height})
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{name}.png"))
    page.set_viewport_size(size)
    print("saved", name)


def store_set(page: Page, store: str, js_assign: str) -> None:
    """Set Pinia state directly, e.g. a date the picker would need many clicks to reach."""
    page.evaluate(
        f"""() => {{
        const pinia = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia;
        const s = pinia._s.get('{store}');
        {js_assign}
    }}"""
    )


def grid_row(page: Page, text: str):
    return page.locator("[data-test=classification] tbody tr", has_text=text).first


HIDE_DEVTOOLS = "#__vue-devtools-container__, [id^=__vue-devtools] { display: none !important }"


def login(page: Page, username: str) -> None:
    page.goto(f"{BASE}/connexion")
    page.fill("#username", username)
    page.fill("#password", PASSWORD)
    page.get_by_role("button", name="Se connecter").click()
    page.wait_for_url(re.compile(r"localhost:5173/(?!connexion)"))
    page.wait_for_load_state("networkidle")


def logout(page: Page) -> None:
    page.context.clear_cookies()


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 860},
        device_scale_factor=1.5,
        locale="fr-FR",
        color_scheme="light",
    )
    ctx.add_init_script(
        "addEventListener('DOMContentLoaded', () => { const st = document.createElement('style');"
        f" st.textContent = '{HIDE_DEVTOOLS}';"
        " document.head.appendChild(st); });"
    )
    page = ctx.new_page()

    # --- Sign in -----------------------------------------------------------
    page.goto(f"{BASE}/connexion")
    page.wait_for_load_state("networkidle")
    shot(page, "01-login")

    page.fill("#username", "demo.direction")
    page.fill("#password", "mauvais-mot-de-passe")
    page.get_by_role("button", name="Se connecter").click()
    page.locator("[data-test=error]").wait_for()
    shot(page, "02-login-error")

    # --- Dashboard and navigation (Direction RH sees every business module) --
    login(page, "demo.direction")
    shot(page, "03-dashboard")
    tall(page, "03b-dashboard-full")

    page.get_by_role("button", name=re.compile("Compte de")).click()
    page.locator("#user-menu").wait_for()
    shot(page, "04-user-menu")
    page.keyboard.press("Escape")

    page.goto(f"{BASE}/compte/mot-de-passe")
    page.wait_for_load_state("networkidle")
    shot(page, "05-password")

    page.goto(f"{BASE}/agents")
    page.wait_for_load_state("networkidle")
    shot(page, "06-module-upcoming")

    # Dark theme
    page.goto(f"{BASE}/")
    page.wait_for_load_state("networkidle")
    page.get_by_role("radio", name="Thème sombre").first.click()
    shot(page, "07-dark-theme")
    page.get_by_role("radio", name="Thème clair").first.click()

    # --- Référentiels --------------------------------------------------------
    page.goto(f"{BASE}/referentiels")
    page.locator("[data-test=tree]").wait_for()
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=expand-all]").click()
    tall(page, "08-organisation")

    page.locator("[data-test=search]").fill("formation")
    page.wait_for_timeout(500)
    shot(page, "09-organisation-search")
    page.locator("[data-test=search]").fill("")

    page.locator("[data-test=date] input").click()
    page.locator(".p-datepicker-panel").wait_for()
    shot(page, "10-organisation-date-picker")
    page.keyboard.press("Escape")
    store_set(page, "referentiels", "s.date = new Date(2024, 5, 1)")
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=expand-all]").click()
    tall(page, "11-organisation-2024")

    page.locator("[data-test=tab-sites]").click()
    page.locator("[data-test=sites]").wait_for()
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=closed-sites]").click()
    page.wait_for_load_state("networkidle")
    shot(page, "12-sites")

    page.locator("[data-test=tab-classification]").click()
    page.locator("[data-test=classification] tbody tr", has_text="Cadres de direction").wait_for()
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=classification-expand-all]").click()
    page.locator("[data-test=classification] tbody tr", has_text="Échelon 1").first.wait_for()
    page.locator("[data-test=classification-collapse-all]").click()
    grid_row(page, "Cadres de collaboration").locator("button").first.click()
    grid_row(page, "Attaché de 2e classe").locator("button").first.click()
    shot(page, "13-classification")

    store_set(page, "referentiels", "s.classification.date = new Date(2024, 5, 1)")
    page.wait_for_load_state("networkidle")
    grid_row(page, "Attaché de 2e classe").wait_for()
    grid_row(page, "Attaché de 2e classe").locator("button").first.click()
    shot(page, "14-classification-2024")

    page.locator("[data-test=tab-fonctions]").click()
    page.locator("[data-test=fonctions] tbody tr", has_text="Chef de service").wait_for()
    page.wait_for_load_state("networkidle")
    tall(page, "14b-fonctions")

    page.locator("[data-test=fonctions-search]").fill("chef")
    page.wait_for_timeout(400)
    shot(page, "14c-fonctions-search")
    page.locator("[data-test=fonctions-search]").fill("")

    store_set(page, "referentiels", "s.fonctions.date = new Date(2023, 11, 31)")
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=fonctions] tbody tr", has_text="Chargé d'études").wait_for()
    page.locator("[data-test=fonctions-search]").fill("etudes")
    page.wait_for_timeout(400)
    shot(page, "14d-fonctions-2023")
    page.locator("[data-test=fonctions-search]").fill("")

    page.locator("[data-test=tab-types-contrat]").click()
    page.locator("[data-test=types-contrat] tbody tr", has_text="Stage").wait_for()
    page.wait_for_load_state("networkidle")
    shot(page, "14e-types-contrat")

    store_set(page, "referentiels", "s.typesContrat.date = new Date(2022, 5, 1)")
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=types-contrat] tbody tr", has_text="apprentissage").wait_for()
    shot(page, "14f-types-contrat-2022")

    page.locator("[data-test=tab-pieces]").click()
    page.locator("[data-test=pieces] tbody tr", has_text="Sortie").wait_for()
    page.wait_for_load_state("networkidle")
    store_set(page, "referentiels", "s.pieces.expanded = {'ev-engagement': true}")
    page.locator("[data-test=pieces] tbody tr", has_text="Contrat signé").wait_for()
    tall(page, "14g-pieces")

    page.locator("[data-test=pieces-search]").fill("decision")
    page.wait_for_timeout(400)
    tall(page, "14h-pieces-decision")
    page.locator("[data-test=pieces-search]").fill("")

    store_set(page, "referentiels", "s.pieces.date = new Date(2023, 5, 1)")
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=pieces-search]").fill("engagement")
    page.locator("[data-test=pieces] tbody tr", has_text="casier").wait_for()
    shot(page, "14i-pieces-2023")
    page.locator("[data-test=pieces-search]").fill("")

    page.locator("[data-test=tab-sorties]").click()
    page.locator("[data-test=suspensions] tbody tr", has_text="Détachement").wait_for()
    page.locator("[data-test=motifs] tbody tr", has_text="Démission").wait_for()
    page.wait_for_load_state("networkidle")
    tall(page, "14j-sorties")

    page.locator("[data-test=sorties-search]").fill("decision")
    page.wait_for_timeout(400)
    tall(page, "14k-sorties-decision")
    page.locator("[data-test=sorties-search]").fill("")

    page.locator("[data-test=tab-banques]").click()
    page.locator("[data-test=banques] tbody tr", has_text="Trésor").wait_for()
    page.wait_for_load_state("networkidle")
    shot(page, "14l-banques")

    store_set(page, "referentiels", "s.banques.date = new Date(2021, 11, 31)")
    page.wait_for_load_state("networkidle")
    page.locator("[data-test=banques] tbody tr", has_text="Union des Banques").wait_for()
    shot(page, "14m-banques-2021")
    store_set(page, "referentiels", "s.banques.date = new Date()")

    # --- Access denied (Social cannot open Paie) -----------------------------
    logout(page)
    login(page, "demo.social")
    shot(page, "15-menu-social")
    page.goto(f"{BASE}/paie")
    page.locator("[data-test=access-denied]").wait_for()
    shot(page, "16-access-denied")

    # --- Audit log and Système (Administrateur système) ----------------------
    logout(page)
    login(page, "demo.admin")
    page.goto(f"{BASE}/audit")
    page.locator(".entries").wait_for()
    page.wait_for_load_state("networkidle")
    page.get_by_placeholder("Auteur").fill("Gestion de carrière")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)
    page.locator("[data-test=module-filter]").click()
    page.wait_for_timeout(300)
    box = page.locator(".p-select-overlay").bounding_box()
    # Crop below the open list, keeping only the first rows of the filtered log.
    clip = {"x": 0, "y": 0, "width": 1366, "height": box["y"] + box["height"] + 110}
    shot(page, "17-audit-module-menu", clip=clip)
    page.get_by_role("option", name="Référentiels").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    shot(page, "18-audit-referentiels")

    rows = page.locator(".entries tbody tr", has_text="Modification")
    rows.filter(has_text="Grade").first.click()
    page.locator("[data-test=audit-panel]").wait_for()
    shot(page, "19-audit-entry")
    page.keyboard.press("Escape")

    page.goto(f"{BASE}/systeme")
    page.locator("[data-test=health]").wait_for()
    shot(page, "20-systeme")

    # --- Narrow screen --------------------------------------------------------
    page.set_viewport_size({"width": 820, "height": 1000})
    page.goto(f"{BASE}/referentiels")
    page.wait_for_load_state("networkidle")
    shot(page, "21-narrow-screen")

    browser.close()
