#!/usr/bin/env python3
"""Pull the whole website from the Notion page "SIF Website" (under SIF Home).

Writes src/data/content.json and downloads member photos into src/assets/members/.
build.py turns that file into the site.

Sources (all under SIF Home > SIF Website, plus the SIF Members database):
  Site Copy     every headline, paragraph, button and question, by Key
  Events        Upcoming and Recent are split by date at build time
  Testimonials  quotes on the home page
  Partners      network partners on the home page
  Leadership    the team list on the About page
  Settings      contact email, member login link, LinkedIn
  SIF Members   members shown on the community page

Publishing rules:
  - Site Copy rows go live only when Status is "Live". A row set to "Editing" keeps the text
    that is on the site now.
  - Every live text passes a compliance check (financial promotion red flags). A row that fails
    is not published: the site keeps the previous text, and the row's Check is set to "Blocked"
    with the reason in Check note. Rows that pass get Check = "OK".
  - Events, Testimonials, Partners and Leadership rows appear only when Show is ticked.
  - Members appear when "Website: Show" is ticked and Conversion Status is a member stage.

"The text on the site now" comes from the live site's /content.json, falling back to the
copy of content.json in the repository.

Settings (environment variables, kept in the hosting provider, never in the page):
  NOTION_TOKEN   a Notion internal integration shared with SIF Website and SIF Members.
                 It needs read access, and update access for the Check columns.
  SITE_URL       optional, defaults to https://sifventures.com

Without NOTION_TOKEN the script leaves content.json untouched, so the build uses the last
synced content. Standard library only; Pillow is used for photos when installed.
"""
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "src/data/content.json"
PHOTOS = ROOT / "src/assets/members"
API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
SITE_URL = os.environ.get("SITE_URL", "https://sifventures.com").rstrip("/")

DATABASES = {
    "copy": "b3ec34548593462aaeea3bc6a49588e4",
    "events": "509162cca3aa4f569eedbd6e22674911",
    "testimonials": "e30033ce0f364cb9a14a6114dbe67076",
    "partners": "420c16cbea8c40d4ba979911f6e3ea3d",
    "leadership": "d0cdf383c5d642098f364cd3c8494396",
    "settings": "2480fc6b468b49d3a6690af08d1ba6d6",
    "members": "258dd62a-dd0d-801a-ad81-d6afc66e1a08",
}
MEMBER_STAGES = {
    "6- Reserved", "7- Collection", "8- Payment in Progress",
    "9- Paid | (Member EFM)", "0- Renewal Fee Due (CM)",
}
SHOW_NAMES = ("website: show", "website show", "show on website")

# Financial promotion red flags. Public pages must not carry returns, deal terms or
# inducements to invest (FSMA 2000 s21, FPO 2005, SIF Terms & Conditions).
RED_FLAGS = [
    (r"\b\d+(?:[.,]\d+)?\s?%", "a percentage figure"),
    (r"\bIRR\b", "IRR"),
    (r"\bMOIC\b", "MOIC"),
    (r"\b\d+(?:\.\d+)?\s?x\b", "a return multiple"),
    (r"guarantee", "a guarantee"),
    (r"risk[- ]free", "'risk-free'"),
    (r"\bvaluation", "a valuation"),
    (r"\b(pre|post)[- ]money\b", "a valuation"),
    (r"\bminimum (ticket|investment|commitment)", "a minimum investment"),
    (r"\b(expected|target|projected|average|historic(al)?)\s+(returns?|yield|irr|gains?)", "a return claim"),
    (r"\b(returns?|yield)\s+of\b", "a return claim"),
    (r"\b(invest now|act now|limited (spots|places|allocation)|don.?t miss|last chance|get in (early|before))", "an inducement to invest"),
    (r"(?-i:\bSPV\b|\bSAFE\b)|\bconvertible note", "an investment instrument"),
]


def check(text):
    for pattern, reason in RED_FLAGS:
        if re.search(pattern, text, re.IGNORECASE):
            return reason
    return None


def call(path, body=None, method=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method or ("POST" if body is not None else "GET"),
        headers={
            "Authorization": "Bearer " + os.environ["NOTION_TOKEN"],
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def query(database_id):
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        page = call(f"/databases/{database_id}/query", body)
        rows += page["results"]
        if not page.get("has_more"):
            return rows
        cursor = page["next_cursor"]


def text(prop):
    if not prop:
        return ""
    kind = prop.get("type")
    if kind in ("title", "rich_text"):
        return "".join(part.get("plain_text", "") for part in prop[kind]).strip()
    if kind == "url":
        return (prop.get("url") or "").strip()
    if kind in ("select", "status"):
        return ((prop.get(kind) or {}).get("name") or "").strip()
    if kind == "number":
        return prop.get("number")
    if kind == "checkbox":
        return bool(prop.get("checkbox"))
    if kind == "date":
        return ((prop.get("date") or {}).get("start") or "")[:10]
    return ""


def first_part(value):
    """Notion often holds several roles as 'Role A; Role B'. Cards show the first."""
    return value.split(";")[0].strip()


def set_check(row, result, note):
    """Write the compliance result back to the row, only when it changed."""
    props = row["properties"]
    if "Check" not in props:
        return
    if text(props.get("Check")) == result and text(props.get("Check note")) == note:
        return
    try:
        call(f"/pages/{row['id']}", {"properties": {
            "Check": {"select": {"name": result}},
            "Check note": {"rich_text": [{"text": {"content": note}}] if note else []},
        }}, method="PATCH")
    except urllib.error.URLError as err:
        print(f"sync_notion: could not write Check for a row ({err})")


def previous_content():
    """What is on the site now: the live /content.json, else the repository copy."""
    try:
        with urllib.request.urlopen(SITE_URL + "/content.json", timeout=15) as resp:
            return json.load(resp)
    except (urllib.error.URLError, ValueError, OSError):
        return json.loads(CONTENT.read_text()) if CONTENT.exists() else {}


def slug(name):
    plain = unicodedata.normalize("NFKD", name.replace("ı", "i").replace("İ", "I"))
    plain = plain.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def save_photo(url, name):
    PHOTOS.mkdir(parents=True, exist_ok=True)
    base = slug(name)
    raw = PHOTOS / (base + ".src")
    with urllib.request.urlopen(url, timeout=60) as resp:
        raw.write_bytes(resp.read())
    try:
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(raw)).convert("RGB")
        img = ImageOps.fit(img, (480, 600), method=Image.LANCZOS, centering=(0.5, 0.35))
        out = PHOTOS / (base + ".webp")
        img.save(out, "WEBP", quality=82, method=6)
        raw.unlink()
    except ImportError:
        out = PHOTOS / (base + ".jpg")
        raw.replace(out)
    return "assets/members/" + out.name


def sync_copy(previous, blocked):
    copy = dict(previous.get("copy", {}))
    for row in query(DATABASES["copy"]):
        props = row["properties"]
        key = text(props.get("Key"))
        if not key:
            continue
        if text(props.get("Status")) != "Live":
            continue  # Editing: keep what is on the site now
        value = text(props.get("Text"))
        reason = check(value)
        if reason:
            blocked.append(f"{text(props.get('Label'))}: {reason}")
            set_check(row, "Blocked", f"Not published: contains {reason}. The site keeps the previous text.")
            continue
        set_check(row, "OK", "")
        copy[key] = value
    return copy


def sync_list(name, fields, previous, blocked, checked=()):
    """Rows with Show ticked. Text fields in `checked` go through the compliance check;
    a failing row keeps its previous version on the site (matched by name)."""
    before = {item.get("name"): item for item in previous.get(name, [])}
    out = []
    for row in query(DATABASES[name]):
        props = row["properties"]
        if "Show" in props and not text(props["Show"]):
            continue
        item = {field: text(props.get(prop)) for field, prop in fields.items()}
        reason = next((r for r in (check(str(item.get(f) or "")) for f in checked) if r), None)
        if reason:
            blocked.append(f"{name.title()} · {item.get('name')}: {reason}")
            set_check(row, "Blocked", f"Not published: contains {reason}. The site keeps the previous version.")
            if item.get("name") in before:
                out.append(before[item["name"]])
            continue
        if checked:
            set_check(row, "OK", "")
        out.append(item)
    return out


def sync_members(previous):
    rows = query(DATABASES["members"])
    if rows and not any(p.get("type") == "checkbox" and k.lower().strip() in SHOW_NAMES
                        for k, p in rows[0]["properties"].items()):
        print('sync_notion: SIF Members has no "Website: Show" checkbox yet; keeping the current member list')
        return previous.get("members", [])
    members, keep = [], set()
    for row in rows:
        props = row["properties"]
        show = next((p for k, p in props.items() if p.get("type") == "checkbox" and k.lower().strip() in SHOW_NAMES), None)
        if not (show and show.get("checkbox")) or text(props.get("Conversion Status")) not in MEMBER_STAGES:
            continue
        name = text(props.get("Name"))
        if not name:
            continue
        photo = ""
        files = next((p for k, p in props.items() if p.get("type") == "files" and ("photo" in k.lower() or "foto" in k.lower())), None)
        if files and files.get("files"):
            f = files["files"][0]
            url = (f.get("file") or f.get("external") or {}).get("url")
            if url:
                try:
                    photo = save_photo(url, name)
                    keep.add(Path(photo).name)
                except (urllib.error.URLError, OSError) as err:
                    print(f"sync_notion: photo for {name} skipped ({err})")
        members.append({
            "name": name,
            "title": text(props.get("Website Title")) or first_part(text(props.get("Unvan"))),
            "company": text(props.get("Website Company")) or first_part(text(props.get("Şirket"))),
            "linkedin": text(props.get("LinkedIn")),
            "photo": photo,
        })
    for old in PHOTOS.glob("*"):
        if old.name not in keep and old.suffix in (".webp", ".jpg", ".jpeg", ".png"):
            old.unlink()  # someone who left the list takes their photo with them
    members.sort(key=lambda m: slug(m["name"]))
    return members


def main():
    if not os.environ.get("NOTION_TOKEN"):
        print("sync_notion: NOTION_TOKEN not set, building from the last synced content")
        return 0
    previous = previous_content()
    blocked = []
    content = {
        "copy": sync_copy(previous, blocked),
        "events": sync_list("events", {"name": "Name", "date": "Date", "time": "Time", "location": "Location",
                                         "description": "Description", "rsvp": "RSVP button"},
                            previous, blocked, checked=("name", "description")),
        "testimonials": sync_list("testimonials", {"name": "Name", "quote": "Quote", "role": "Role",
                                                     "featured": "Featured", "order": "Order"},
                                  previous, blocked, checked=("quote",)),
        "partners": sync_list("partners", {"name": "Name", "link": "Link", "order": "Order"}, previous, blocked),
        "leadership": sync_list("leadership", {"name": "Name", "role": "Role", "order": "Order"}, previous, blocked),
        "settings": dict(previous.get("settings", {})),
        "members": sync_members(previous),
    }
    for row in query(DATABASES["settings"]):
        key, value = text(row["properties"].get("Key")), text(row["properties"].get("Value"))
        if key and value:
            content["settings"][key] = value
    CONTENT.write_text(json.dumps(content, ensure_ascii=False, indent=1) + "\n")
    print(f"sync_notion: {len(content['copy'])} texts, {len(content['events'])} events, "
          f"{len(content['members'])} members")
    for line in blocked:
        print("sync_notion: BLOCKED", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
