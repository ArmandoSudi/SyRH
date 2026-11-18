"""Build docs/user-guide.html from docs/user-guide.md.

The page is self-contained: the screenshots are embedded, so the one file can be emailed or
copied anywhere. From the repository root:

    uv run --no-project --with markdown python docs/build_user_guide.py
"""

import base64
import re
from pathlib import Path

import markdown
from markdown.extensions.toc import slugify_unicode

DOCS = Path(__file__).resolve().parent
SOURCE = DOCS / "user-guide.md"
TARGET = DOCS / "user-guide.html"

STYLE = """
:root {
  --bg: #f4f4f0; --surface: #ffffff; --text: #1b1b19; --muted: #66665f;
  --border: #e3e3dc; --accent: #c8f04e; --code: #efefe9;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161615; --surface: #20201e; --text: #ecece6; --muted: #a3a39b;
    --border: #34342f; --accent: #c8f04e; --code: #2a2a27;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.6 "Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
}
main {
  max-width: 54rem; margin: 2rem auto; padding: 2.5rem 3rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 1.25rem;
}
h1 { font-size: 2.1rem; letter-spacing: -0.02em; margin-top: 0; }
h1::before {
  content: "S"; display: inline-grid; place-items: center; width: 2.4rem; height: 2.4rem;
  margin-right: 0.75rem; border-radius: 0.6rem; background: var(--accent); color: #1b1b19;
  font-size: 1.3rem; vertical-align: 0.2rem;
}
h2 {
  margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border);
  font-size: 1.5rem; letter-spacing: -0.01em;
}
h3 { margin-top: 2rem; font-size: 1.15rem; }
a { color: inherit; text-decoration-color: var(--accent); text-decoration-thickness: 2px; }
blockquote {
  margin: 1.5rem 0; padding: 0.9rem 1.2rem; border-left: 4px solid var(--accent);
  background: var(--code); border-radius: 0 0.75rem 0.75rem 0;
}
blockquote p { margin: 0; }
code { background: var(--code); padding: 0.1rem 0.35rem; border-radius: 0.35rem; font-size: 0.9em; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.93rem; }
th, td { text-align: left; padding: 0.55rem 0.7rem; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; }
figure { margin: 1.25rem 0 1.75rem; }
figure img {
  display: block; width: 100%; height: auto;
  border: 1px solid var(--border); border-radius: 0.75rem;
}
figcaption { margin-top: 0.5rem; color: var(--muted); font-size: 0.88rem; text-align: center; }
hr { border: 0; border-top: 1px solid var(--border); margin: 2.5rem 0; }
@media (max-width: 720px) {
  main { margin: 0; padding: 1.5rem 1rem; border-radius: 0; border: 0; }
  table { display: block; overflow-x: auto; }
}
@media print {
  body { background: #fff; }
  main { border: 0; margin: 0; padding: 0; max-width: none; }
  h2 { break-before: page; border-top: 0; }
  figure { break-inside: avoid; }
}
"""


def embed(match: re.Match) -> str:
    """Turn an image paragraph into a figure with a caption and the PNG inline."""
    alt, src = match.group(1), match.group(2)
    data = base64.b64encode((DOCS / src).read_bytes()).decode()
    return (
        f'<figure><img src="data:image/png;base64,{data}" alt="{alt}" loading="lazy">'
        f"<figcaption>{alt}</figcaption></figure>"
    )


def main() -> None:
    body = markdown.markdown(
        SOURCE.read_text(),
        extensions=["tables", "toc", "sane_lists"],
        # Same anchors as GitHub's, so the links of the contents work in both.
        extension_configs={"toc": {"slugify": slugify_unicode}},
        output_format="html",
    )
    body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)"\s*/?></p>', embed, body)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SyRH user guide</title>
<style>{STYLE}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""
    TARGET.write_text(html)
    print(f"wrote {TARGET.relative_to(DOCS.parent)} ({len(html) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
