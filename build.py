#!/usr/bin/env python3
"""Build the SIF Ventures website.

    python3 build.py            -> public/   (the real site, root-absolute links)
    python3 build.py --preview  -> preview/  (self-contained copy for a private review link)

Each page lives in src/pages/<name>.html. Its first line is a comment with the page's
settings:  <!-- path: about-us | title: About | description: ... -->
Inside pages, write links as {{link:about-us}} or {{link:}} for home, and the shared
contact address as {{email}}. Everything else is plain HTML.
"""
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
PREVIEW = "--preview" in sys.argv
OUT = ROOT / ("preview" if PREVIEW else "public")

SITE_URL = "https://sifventures.com"
EMAIL = "team@sifventures.com"
LOGIN_URL = "/login/"  # decide where member login points once WordPress is retired

NAV = [
    ("about-us", "About"),
    ("membership", "Membership"),
    ("portfolio", "Opportunities"),
    ("events", "Events"),
    ("community", "Community"),
]

ARROW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>')
ARROW_UP_RIGHT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                  '<path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>')


def wordmark(label=True):
    """The approved wordmark, inked with currentColor (navy or off-white, set by CSS)."""
    src = (SRC / "assets/brand/wordmark-source.svg").read_text()
    g = re.search(r"<g[^>]*>.*</g>", src, re.S).group(0)
    g = g.replace('fill="#000000"', 'fill="currentColor"')
    aria = 'role="img" aria-label="SIF Ventures"' if label else 'aria-hidden="true"'
    return (f'<svg viewBox="1034 886 6140 628" xmlns="http://www.w3.org/2000/svg" {aria}>'
            f"{g}</svg>")


def depth(path):
    return 0 if path == "" else path.count("/") + 1


def link(target, current_path):
    target = target.strip("/")
    anchor = ""
    if "#" in target:
        target, anchor = target.split("#", 1)
        anchor = "#" + anchor
    if not PREVIEW:
        return ("/" if target == "" else f"/{target}/") + anchor
    up = "../" * depth(current_path)
    return f"{up}{target + '/' if target else ''}index.html{anchor}"


def mailto(subject):
    from urllib.parse import quote
    return f"mailto:{EMAIL}?subject={quote(subject)}"


def render(template, page_path):
    template = re.sub(r"\{\{link:([^}]*)\}\}", lambda m: link(m.group(1), page_path), template)
    template = re.sub(r"\{\{mailto:([^}]*)\}\}", lambda m: mailto(m.group(1)), template)
    template = template.replace("{{email}}", EMAIL)
    template = template.replace("{{arrow}}", ARROW).replace("{{arrow-out}}", ARROW_UP_RIGHT)
    template = template.replace("{{login}}", LOGIN_URL if not PREVIEW else link("membership", page_path))
    return template


def header(page_path):
    items = []
    for target, label in NAV:
        current = ' aria-current="page"' if page_path.split("/")[0] == target or (
            target == "membership" and page_path in ("founding-membership", "club-membership")) else ""
        items.append(f'<a href="{{{{link:{target}}}}}"{current}>{label}</a>')
    nav = "".join(items)
    return f"""
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{{{{link:}}}}">{wordmark()}</a>
    <nav class="nav" aria-label="Main">{nav}</nav>
    <a class="btn btn--primary header-cta" href="{{{{link:membership#apply}}}}">Request an invitation</a>
    <details class="menu">
      <summary>Menu</summary>
      <nav class="menu-panel" aria-label="Main">{nav}<a class="btn btn--primary" href="{{{{link:membership#apply}}}}">Request an invitation</a></nav>
    </details>
  </div>
</header>"""


FOOTER = """
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-top">
      <div>
        <a class="brand" href="{{link:}}">%(logo)s</a>
        <p style="max-width:34ch">A referral-only network compounding social, intellectual and financial capital. United Kingdom, Türkiye and Bulgaria.</p>
      </div>
      <div>
        <p class="eyebrow">Navigate</p>
        <a href="{{link:about-us}}">About</a>
        <a href="{{link:membership}}">Membership</a>
        <a href="{{link:portfolio}}">Opportunities</a>
        <a href="{{link:events}}">Events</a>
        <a href="{{link:community}}">Community</a>
      </div>
      <div>
        <p class="eyebrow">Membership</p>
        <a href="{{link:founding-membership}}">Founding membership</a>
        <a href="{{link:club-membership}}">Club membership</a>
        <a href="{{login}}">Member login</a>
      </div>
      <div>
        <p class="eyebrow">Contact</p>
        <a href="mailto:{{email}}">{{email}}</a>
        <a href="https://www.linkedin.com/company/smartinvestmentforum" rel="noopener">LinkedIn</a>
        <span>UK · TR · BG</span>
      </div>
    </div>
    <div class="footer-legal">
      <p>SIF Ventures Ltd is not authorised or regulated by the Financial Conduct Authority. Nothing on this site is an offer, invitation or solicitation to invest, and nothing on it is investment advice. SIF acts as an intermediary that brings opportunities to its members. It does not invest on their behalf.</p>
      <p>Information about specific opportunities is shared only inside the private member group, with members who have self-certified as high-net-worth individuals or sophisticated investors. Investing in private markets carries a high risk, including illiquidity and the loss of all capital invested.</p>
      <p>© 2026 SIF Ventures Ltd. All rights reserved.</p>
    </div>
  </div>
</footer>"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
"""


def build_page(src_file, css, js):
    raw = src_file.read_text()
    meta_line, body = raw.split("\n", 1)
    meta = dict(part.split(":", 1) for part in meta_line.strip()[4:-3].split(" | "))
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    path = meta["path"]
    title = meta["title"]
    full_title = "SIF Ventures" if title == "SIF Ventures" else f"{title} | SIF Ventures"
    if PREVIEW and path == "":
        full_title = "SIF Ventures Website"
    desc = html.escape(meta["description"], quote=True)
    canonical = SITE_URL + ("/" if path == "" else f"/{path}/")

    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=League+Spartan:wght@400;600;700&'
             'family=Montserrat:wght@500;600;700&family=Roboto:wght@400;500&family=Radley&display=swap">')
    head_meta = (f"<title>{html.escape(full_title)}</title>\n"
                 '<meta name="claude:viewport-fit-sides" content="cover">\n'
                 f'<meta name="description" content="{desc}">\n'
                 f'<link rel="canonical" href="{canonical}">\n'
                 f'<meta property="og:title" content="{html.escape(full_title)}">\n'
                 f'<meta property="og:description" content="{desc}">\n'
                 '<meta property="og:type" content="website">\n'
                 f'<meta property="og:url" content="{canonical}">\n'
                 '<meta name="theme-color" content="#0e162c">\n')
    if PREVIEW:
        styles = f"<style>\n{css}\n</style>"
        script = f"<script>\n{js}\n</script>"
    else:
        head_meta += '<link rel="icon" href="/assets/brand/favicon.svg" type="image/svg+xml">\n'
        styles = '<link rel="stylesheet" href="/assets/css/site.css">'
        script = '<script src="/assets/js/site.js" defer></script>'

    page = (header(path) + f'\n<main id="main">\n{body}\n</main>\n' + (FOOTER % {"logo": wordmark(False)}))
    page = render(page, path)

    is_artifact_main = PREVIEW and path == ""
    if is_artifact_main:  # the preview host wraps its main page in its own document skeleton
        doc = f"{head_meta}{fonts}\n{styles}\n{page}\n{script}\n"
    else:
        doc = f"{HEAD}{head_meta}{fonts}\n{styles}\n</head>\n<body>\n{page}\n{script}\n</body>\n</html>\n"

    out_file = OUT / path / "index.html" if path else OUT / "index.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(doc)
    return out_file


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    css = (SRC / "assets/css/site.css").read_text()
    js = (SRC / "assets/js/site.js").read_text()
    built = [build_page(f, css, js) for f in sorted((SRC / "pages").glob("*.html"))]
    if not PREVIEW:
        shutil.copytree(SRC / "assets", OUT / "assets")
        mono = (SRC / "assets/brand/monogram-source.svg").read_text().split("?>", 1)[-1]
        mono = mono.replace('fill="#000000"', 'fill="#0e162c"')
        (OUT / "assets/brand/favicon.svg").write_text(mono)
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
        urls = "".join(
            f"<url><loc>{SITE_URL}/{p.parent.relative_to(OUT).as_posix() + '/' if p.parent != OUT else ''}</loc></url>"
            for p in built)
        (OUT / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    for p in built:
        print("built", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
