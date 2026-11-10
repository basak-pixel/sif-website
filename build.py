#!/usr/bin/env python3
"""Build the SIF Ventures website.

    python3 build.py            -> public/   (the real site, root-absolute links)
    python3 build.py --preview  -> preview/  (self-contained copy for a private review link)

Layout lives in src/pages/<name>.html; all words live in src/data/content.json, which
scripts/sync_notion.py fills from the Notion page "SIF Website" (SIF Home > SIF Website).

Page templates use these slots:
  {{t:key}}           a text from Site Copy (escaped)
  {{lines:key}}       a headline, one line per line break in Notion
  {{link:about-us}}   a link to a page ({{link:}} for home, {{link:membership#apply}} for an anchor)
  {{mailto:Subject}}  an email link to the contact address with a subject
  {{email}}           the contact address
  {{members}} {{testimonials}} {{partners}} {{leadership}} {{events_upcoming}} {{events_past}}
                      sections generated from their Notion tables
The first line of each page is a comment with its path: <!-- path: about-us | ... -->
"""
import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
PREVIEW = "--preview" in sys.argv
OUT = ROOT / ("preview" if PREVIEW else "public")

SITE_URL = "https://sifventures.com"
CONTENT = json.loads((SRC / "data/content.json").read_text())
COPY = CONTENT.get("copy", {})
SETTINGS = CONTENT.get("settings", {})
EMAIL = SETTINGS.get("contact_email", "team@sifventures.com")
LOGIN_URL = SETTINGS.get("login_url", "/login/")
MYSIF_URL = SETTINGS.get("mysif_url") or LOGIN_URL  # "MY SIF link" in Notion Settings
LINKEDIN_URL = SETTINGS.get("linkedin_url", "https://www.linkedin.com/company/smartinvestmentforum")
MISSING = set()

NAV = [
    ("about-us", "About"),
    ("membership", "Membership"),
    ("portfolio", "Opportunities"),
    ("events", "Events"),
    ("community", "Community"),
]

ARROW = ""  # buttons carry no decorative arrows; external links keep ARROW_UP_RIGHT
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


def hero_art():
    """The SIF monogram as a hairline drawing for the hero. Strokes draw themselves on load;
    the top bar of the F is the one gold line."""
    src = (SRC / "assets/brand/monogram-source.svg").read_text()
    paths = re.findall(r'<path d="([^"]+)"', src)
    names = ["s", "f-bar", "i", "f-stem"]
    drawn = "".join(f'<path class="m-{n}" pathLength="1" d="{d}"/>' for n, d in zip(names, paths))
    # signals: short bright segments that keep travelling along each stroke after it is drawn
    drawn += "".join(f'<path class="trace t-{n}" pathLength="1" d="{d}"/>' for n, d in zip(names, paths))
    return ('<div class="hero-glow" aria-hidden="true"></div><div class="hero-art" aria-hidden="true"><svg viewBox="600 930 1230 660" '
            'preserveAspectRatio="xMaxYMid meet"><g transform="translate(0,2362) scale(0.1,-0.1)">'
            f"{drawn}</g></svg></div>")


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


def initials(name):
    parts = [p for p in name.replace("-", " ").split() if p]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def members_grid(page_path):
    """Member cards for the community page (SIF Members in Notion)."""
    members = CONTENT.get("members", [])
    cards = []
    for m in members:
        name = html.escape(m["name"])
        if m.get("photo"):
            src = m["photo"] if PREVIEW is False else "../" * depth(page_path) + m["photo"]
            src = "/" + src if not PREVIEW else src
            portrait = (f'<img src="{html.escape(src)}" alt="" width="480" height="600" '
                        f'loading="lazy" decoding="async">')
        else:
            portrait = f'<span class="initials" aria-hidden="true">{html.escape(initials(m["name"]))}</span>'
        role = "".join(
            f'<span class="{cls}">{html.escape(m[key])}</span>'
            for key, cls in (("title", "member-title"), ("company", "member-company")) if m.get(key))
        inner = (f'<span class="portrait">{portrait}</span>'
                 f'<span class="member-name">{name}</span>{role}')
        if m.get("linkedin"):
            inner = (f'<a class="member-link" href="{html.escape(m["linkedin"])}" rel="noopener" '
                     f'aria-label="{name} on LinkedIn">{inner}<span class="member-out">{ARROW_UP_RIGHT}</span></a>')
        else:
            inner = f'<div class="member-link">{inner}</div>'
        cards.append(f"<li>{inner}</li>")
    return len(members), '<ul class="members">' + "".join(cards) + "</ul>"


def copy(key):
    if key not in COPY:
        MISSING.add(key)
    return COPY.get(key, "").replace("{count}", str(len(CONTENT.get("members", []))))


def headline_lines(key):
    lines = [l.strip() for l in copy(key).split("\n") if l.strip()]
    return "".join(f'<span class="ln"><span>{html.escape(l)}</span></span>' for l in lines)


def by_order(items):
    return sorted(items, key=lambda i: (i.get("order") is None, i.get("order") or 0, i.get("name", "")))


def testimonials():
    items = by_order(CONTENT.get("testimonials", []))
    if not items:
        return ""
    featured = next((t for t in items if t.get("featured")), items[0])
    rest = [t for t in items if t is not featured]

    def fig(t, cls):
        role = f'<span>{html.escape(t["role"])}</span>' if t.get("role") else ""
        return (f'<figure class="{cls}"><blockquote>\u201c{html.escape(t["quote"].strip("\u201c\u201d\""))}\u201d</blockquote>'
                f'<figcaption><strong>{html.escape(t["name"])}</strong>{role}</figcaption></figure>')
    out = fig(featured, "quote quote--lg")
    if rest:
        out += '<div class="quote-stack">' + "".join(fig(t, "quote quote--sm") for t in rest) + "</div>"
    return f'<div class="testimonials">{out}</div>'


def partners():
    items = by_order(CONTENT.get("partners", []))
    lis = "".join(
        f'<li><a href="{html.escape(p["link"])}" rel="noopener">{html.escape(p["name"])} {ARROW_UP_RIGHT}</a></li>'
        if p.get("link") else f'<li><a>{html.escape(p["name"])}</a></li>' for p in items)
    return f'<ul class="partners">{lis}</ul>'


def leadership():
    items = by_order(CONTENT.get("leadership", []))
    lis = "".join(f'<li><span class="name">{html.escape(p["name"])}</span>'
                  f'<span class="role">{html.escape(p.get("role", ""))}</span></li>' for p in items)
    return f'<ul class="people">{lis}</ul>'


def events(upcoming):
    today = datetime.date.today().isoformat()
    items = [e for e in CONTENT.get("events", []) if e.get("date")]
    items = [e for e in items if (e["date"] >= today) == upcoming]
    items.sort(key=lambda e: e["date"], reverse=not upcoming)
    if not upcoming:
        items = items[:6]
    if not items:
        return f'<p class="lead">{html.escape(copy("events.upcoming.empty"))}</p>' if upcoming else ""
    out = []
    for e in items:
        d = datetime.date.fromisoformat(e["date"])
        small = f'{d.year}, {e["time"]}' if e.get("time") and upcoming else str(d.year)
        when = f'<p class="when">{d.day} {d.strftime("%b")}<small>{html.escape(small)}</small></p>'
        body = (f'<div class="stack" style="gap:8px"><h3>{html.escape(e["name"])}</h3>'
                + (f'<p class="meta">{html.escape(e["location"])}</p>' if e.get("location") else "")
                + (f'<p>{html.escape(e["description"])}</p>' if e.get("description") else "") + "</div>")
        if upcoming:
            action = (f'<a class="btn btn--tonal" href="{{{{mailto:{e["name"]} RSVP}}}}">RSVP</a>'
                      if e.get("rsvp") else "<span></span>")
        else:
            action = '<span class="badge badge--quiet">Held</span>'
        out.append(f'<article class="event">{when}{body}{action}</article>')
    return "<div>" + "".join(out) + "</div>"


def render(template, page_path):
    if "{{members}}" in template:
        count, grid = members_grid(page_path)
        template = template.replace("{{members}}", grid)
    template = template.replace("{{hero_art}}", hero_art() if "{{hero_art}}" in template else "")
    template = (template.replace("{{testimonials}}", testimonials() if "{{testimonials}}" in template else "")
                .replace("{{partners}}", partners() if "{{partners}}" in template else "")
                .replace("{{leadership}}", leadership() if "{{leadership}}" in template else "")
                .replace("{{events_upcoming}}", events(True) if "{{events_upcoming}}" in template else "")
                .replace("{{events_past}}", events(False) if "{{events_past}}" in template else ""))
    template = re.sub(r"\{\{lines:([^}]+)\}\}", lambda m: headline_lines(m.group(1)), template)
    template = re.sub(r"\{\{t:([^}]+)\}\}", lambda m: html.escape(copy(m.group(1)), quote=False), template)
    template = re.sub(r"\{\{link:([^}]*)\}\}", lambda m: link(m.group(1), page_path), template)
    template = re.sub(r"\{\{mailto:([^}]*)\}\}", lambda m: mailto(m.group(1)), template)
    template = template.replace("{{email}}", EMAIL)
    template = template.replace("{{arrow}}", ARROW).replace("{{arrow-out}}", ARROW_UP_RIGHT)
    template = template.replace("{{login}}", LOGIN_URL if not PREVIEW else link("membership", page_path))
    template = template.replace("{{mysif}}", MYSIF_URL if not (PREVIEW and MYSIF_URL.startswith("/")) else "#")
    template = template.replace("{{linkedin}}", LINKEDIN_URL)
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
    <div class="header-actions">
      <a class="btn btn--line btn--sm" href="{{{{mysif}}}}">{{{{t:global.header.mysif}}}}</a>
      <a class="btn btn--primary btn--sm header-cta" href="{{{{link:membership#apply}}}}">{{{{t:global.header.cta}}}}</a>
    </div>
  </div>
</header>"""


FOOTER = """
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-top">
      <div>
        <a class="brand" href="{{link:}}">%(logo)s</a>
        <p style="max-width:34ch">{{t:global.footer.blurb}}</p>
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
        <a href="{{mysif}}">{{t:global.header.mysif}}</a>
      </div>
      <div>
        <p class="eyebrow">Contact</p>
        <a href="mailto:{{email}}">{{email}}</a>
        <a href="{{linkedin}}" rel="noopener">LinkedIn</a>
        <span>United Kingdom, Türkiye, Bulgaria</span>
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
    pkey = path or "home"
    title = copy(f"{pkey}.meta.title") or meta.get("title", "SIF Ventures")
    full_title = title if "SIF Ventures" in title else f"{title} | SIF Ventures"
    if PREVIEW and path == "":
        full_title = "SIF Ventures Website"
    desc = html.escape(copy(f"{pkey}.meta.description") or meta.get("description", ""), quote=True)
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
    if PREVIEW and (SRC / "assets/members").exists():
        shutil.copytree(SRC / "assets/members", OUT / "assets/members")
    if not PREVIEW:
        shutil.copytree(SRC / "assets", OUT / "assets", ignore=shutil.ignore_patterns("*.src"))
        mono = (SRC / "assets/brand/monogram-source.svg").read_text().split("?>", 1)[-1]
        mono = mono.replace('fill="#000000"', 'fill="#0e162c"')
        (OUT / "assets/brand/favicon.svg").write_text(mono)
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
        urls = "".join(
            f"<url><loc>{SITE_URL}/{p.parent.relative_to(OUT).as_posix() + '/' if p.parent != OUT else ''}</loc></url>"
            for p in built)
        (OUT / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
        (OUT / "content.json").write_text(json.dumps(CONTENT, ensure_ascii=False))  # read back by the next sync
    for p in built:
        print("built", p.relative_to(ROOT))
    if MISSING:
        print("missing texts (add these keys in Site Copy):", ", ".join(sorted(MISSING)))


if __name__ == "__main__":
    main()
