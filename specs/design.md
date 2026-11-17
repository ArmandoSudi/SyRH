# Design system

How SyRH looks and why. The live reference is the **Design** page of the app (`/design`); the
tokens are in [`frontend/src/shared/theme/tokens.css`](../frontend/src/shared/theme/tokens.css) and the
PrimeVue preset in [`frontend/src/shared/theme/preset.ts`](../frontend/src/shared/theme/preset.ts).

## Where it comes from

The look is derived from five reference dashboards supplied by the project owner: two dark
analytics dashboards, and three light workspace dashboards. We kept the traits they share and
dropped what is specific to one of them.

| Trait in the references | What SyRH does |
| --- | --- |
| One vivid lime accent on a neutral canvas | Lime is the brand colour, used as a fill |
| Violet and orange as secondary accents | Second and third data series, avatars, attention |
| Near-black canvas with slightly lighter cards (dark) | Dark theme surfaces |
| Warm off-white canvas with white cards (light) | Light theme surfaces |
| Large rounded cards, pill buttons, round icon badges | Radius scale from 10px to 24px, pill controls |
| One highlighted KPI card per row, solid accent | `StatCard` with `featured` |
| Pill-shaped bars with the value in a bubble | `PillBars` |
| Diagonal hatching for the remaining or forecast part | `.sy-hatch`, `ProgressPill`, bar extras |
| Thick donut with rounded, separated segments | `DonutChart` |
| Black pill for the active item (light), lime (dark) | The `inverse` token pair |
| Round geometric sans-serif, bold figures | Plus Jakarta Sans, tabular numbers |

## Principles

1. **Calm canvas, one loud colour.** Most of the screen is neutral. Lime marks the one thing
   that matters most in a view: the featured figure, the primary action, the active state.
2. **Lime is a fill, never text.** It has too little contrast on white. Text on lime is always
   `--sy-on-lime` (near-black). Text, outlined and link buttons use `secondary` or `contrast`.
3. **Colour is never the only signal.** Statuses carry a label; chart series carry a legend.
4. **Hatching means "not actual".** Remaining, planned, vacant, forecast. Never a realised value.
5. **Data first.** HR screens are tables and forms; decoration must not cost density. Charts
   appear on dashboards, not on data-entry screens.
6. **Both themes are first-class.** Every screen is checked in light and dark before merge.

## Themes

Three modes: light, dark, and system (default). The choice is stored in `localStorage` under
`syrh-theme` and applied before first paint by an inline script in `index.html`, so there is no
flash. The theme store (`src/shared/theme/store.ts`) toggles `html.dark`.

Each colour is declared **once** with the CSS `light-dark()` function, and `color-scheme`
switches with `html.dark`. Components never contain theme-specific rules; they only read tokens.
PrimeVue follows the same class through `darkModeSelector: '.dark'`.

## Colour tokens

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--sy-bg` | `#f1f2ec` | `#121311` | Page canvas |
| `--sy-surface` | `#ffffff` | `#1e1f1c` | Cards, sidebar |
| `--sy-surface-2` | `#f6f7f2` | `#272824` | Hover, nested areas |
| `--sy-surface-3` | `#eeefe8` | `#32342e` | Icon badges, tracks |
| `--sy-border` | `#e2e4da` | `#32342e` | Hairlines |
| `--sy-text` | `#14160f` | `#f2f3ee` | Text |
| `--sy-muted` | `#5d6154` | `#a3a798` | Secondary text |
| `--sy-lime` | `#c6f04d` | `#d2f65a` | Brand, primary series |
| `--sy-violet` | `#8b7cf6` | `#9d90fa` | Second series |
| `--sy-orange` | `#ff8a3d` | `#ff9a57` | Third series, attention |
| `--sy-inverse` | `#14160f` | `#d2f65a` | Active nav item, selected toggle |
| `--sy-success` | `#1f7a44` | `#5bd68a` | Validated, positive change |
| `--sy-warning` | `#a85a00` | `#ffb066` | Pending, deadline near |
| `--sy-danger` | `#b42318` | `#ff8d85` | Rejected, negative change |

Each accent has an `--sy-on-*` partner for content placed on it. Status colours have `-soft`
backgrounds. Neutrals are slightly warm (olive-grey) so that lime sits naturally on them.

Chart series order is fixed: lime, violet, orange, then muted grey.

## Typography

Plus Jakarta Sans, self-hosted through `@fontsource-variable` (no external font request, since
SyRH runs on the ARPTC network). Base size 15px.

| Role | Size | Weight |
| --- | --- | --- |
| Page title | 1.6rem | 600 |
| Card title | 1.05rem | 600 |
| Body | 1rem | 400 |
| Caption, legend | 0.8–0.85rem | 400 |
| Key figure | 1.75rem | 700 |
| Group label | 0.72rem uppercase | 600 |

Figures that are compared (amounts, counts, dates) use `.sy-num` for tabular digits. Amounts
are written the French way with their unit: `1 024 300 USD`, `94 %`.

## Shape, spacing, elevation

- **Radius**: 10px (small controls), 14px (fields), 20px (bars), 24px (cards), pill (buttons,
  tags, nav items, progress).
- **Spacing**: a 4px-based scale, `--sy-space-1` (4px) to `--sy-space-6` (32px). Cards have 24px
  padding and 16px gaps.
- **Elevation**: none in dark mode; a barely visible shadow in light mode. Separation comes from
  surface contrast and a 1px border, not from shadows.

## Layout

- **Sidebar** (248px): brand, main modules, then an Administration group. The active item is an
  `inverse` pill. Below 1000px it collapses to an icon rail.
- **Top bar**: page title on the left; search, theme toggle, notifications, user on the right.
- **Content**: a fluid grid of cards that wraps by itself (`auto-fit`), so there is no horizontal
  page scroll at any width.

## Components

| Component | Purpose |
| --- | --- |
| `.sy-card`, `.sy-card-header`, `.sy-card-title` | The standard panel |
| `.sy-icon` | Round icon badge |
| `.sy-hatch`, `.sy-legend`, `.sy-num`, `.sy-muted` | Utilities |
| `StatCard` | Key figure with trend; `featured` for the lime one |
| `PillBars` | Vertical pill bar chart with optional hatched extra |
| `DonutChart` | Parts of a whole with a legend table |
| `ProgressPill` | Progress with hatched remainder |
| `ThemeToggle` | Light / dark / system switch |
| `AppShell` | Sidebar and top bar around every screen |

Form controls, tables, tags, dialogs and pickers come from **PrimeVue**, themed by the preset.
Build a custom component only when PrimeVue has none.

Status mapping for PrimeVue `Tag`: Validé → `success`, En attente → `warn`, Rejeté → `danger`,
Brouillon → `info`, Archivé → `secondary`.

## Charts

Charts that need axes, tooltips or time series use **Apache ECharts** (see
[`tech-stack.md`](tech-stack.md)), styled to match the hand-built ones: series order lime,
violet, orange, grey; bars and donut segments rounded; ECharts "decal" patterns for the hatched
"not actual" parts; colours read from the tokens so both themes work.

## Icons

PrimeIcons, outline style, one icon per module in the sidebar. Icons accompany a label; an
icon-only control always has an `aria-label` and a `title`.

## Accessibility

- Text colours are chosen for WCAG AA contrast on their surface in both themes. This has not
  been audited with a tool yet.
- Every interactive element has a visible focus ring.
- Charts expose a text alternative (`aria-label`) and show their values as text.
- SyRH is a desktop back office first. It still reflows down to phone width without horizontal
  scrolling: the sidebar becomes an icon rail and the page title truncates.

## Not decided yet

- Print styles for payslips and certificates.
- The definitive logo; the lime "S" mark is a placeholder.
