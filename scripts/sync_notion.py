#!/usr/bin/env python3
"""Pull the public member list from the Notion "SIF Members" database.

Writes src/data/members.json and downloads photos into src/assets/members/.
build.py turns that file into the community page.

Who appears on the website (both must be true):
  1. The "Website: Show" checkbox is ticked. This is the member's consent to be listed.
  2. Their Conversion Status is a member stage (see MEMBER_STAGES below).
So moving someone up the funnel adds them, and moving them out (Park, Not a Fit,
Closed) removes them on the next build.

Card fields:
  Name      -> "Name"
  Title     -> "Website Title" if that property exists and is filled, else the first role in "Unvan"
  Company   -> "Website Company" if present, else the first company in "Şirket"
  LinkedIn  -> "LinkedIn"
  Photo     -> the first file in "Website Photo" (any files property whose name contains "photo"/"foto")

Settings (environment variables, kept in the hosting provider, never in the page):
  NOTION_TOKEN        an internal integration token with read access to SIF Members
  NOTION_DATABASE_ID  optional; defaults to the SIF Members database

If NOTION_TOKEN is missing, the script leaves the existing members.json untouched,
so a build without Notion access still produces the last known list.
Only the standard library is required. Pillow is used to resize photos when installed.
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
DATA = ROOT / "src/data/members.json"
PHOTOS = ROOT / "src/assets/members"
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "258dd62a-dd0d-801a-ad81-d6afc66e1a08")
API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

MEMBER_STAGES = {
    "6- Reserved",
    "7- Collection",
    "8- Payment in Progress",
    "9- Paid | (Member EFM)",
    "0- Renewal Fee Due (CM)",
}
SHOW_NAMES = ("website: show", "website show", "show on website", "website")


def call(path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET",
        headers={
            "Authorization": "Bearer " + os.environ["NOTION_TOKEN"],
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def text(prop):
    if not prop:
        return ""
    kind = prop.get("type")
    if kind in ("title", "rich_text"):
        return "".join(part.get("plain_text", "") for part in prop[kind]).strip()
    if kind == "url":
        return (prop.get("url") or "").strip()
    if kind == "select":
        return (prop.get("select") or {}).get("name", "")
    if kind == "status":
        return (prop.get("status") or {}).get("name", "")
    if kind == "formula":
        return str((prop.get("formula") or {}).get("string") or "")
    return ""


def first_part(value):
    """Notion often holds several roles as 'Role A; Role B'. The card shows the first."""
    return value.split(";")[0].strip()


def find_prop(props, wanted_type, names=None, contains=None):
    for key, prop in props.items():
        if prop.get("type") != wanted_type:
            continue
        low = key.lower().strip()
        if names and low in names:
            return prop
        if contains and any(word in low for word in contains):
            return prop
    return None


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


def main():
    if not os.environ.get("NOTION_TOKEN"):
        print("sync_notion: NOTION_TOKEN not set, keeping the existing member list")
        return 0

    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        page = call(f"/databases/{DATABASE_ID}/query", body)
        rows += page["results"]
        if not page.get("has_more"):
            break
        cursor = page["next_cursor"]

    if rows and not find_prop(rows[0]["properties"], "checkbox", names=SHOW_NAMES):
        print('sync_notion: no "Website: Show" checkbox found in SIF Members. '
              "Add it, tick the members who agreed to be listed, then build again.")
        return 1

    members, keep_photos = [], set()
    for row in rows:
        props = row["properties"]
        show = find_prop(props, "checkbox", names=SHOW_NAMES)
        stage = text(props.get("Conversion Status"))
        if not (show and show.get("checkbox")) or stage not in MEMBER_STAGES:
            continue
        name = text(props.get("Name"))
        if not name:
            continue
        title = text(props.get("Website Title")) or first_part(text(props.get("Unvan")))
        company = text(props.get("Website Company")) or first_part(text(props.get("Şirket")))
        photo = ""
        files = find_prop(props, "files", contains=("photo", "foto"))
        if files and files.get("files"):
            f = files["files"][0]
            url = (f.get("file") or f.get("external") or {}).get("url")
            if url:
                try:
                    photo = save_photo(url, name)
                    keep_photos.add(Path(photo).name)
                except (urllib.error.URLError, OSError) as err:
                    print(f"sync_notion: photo for {name} skipped ({err})")
        members.append({
            "name": name,
            "title": title,
            "company": company,
            "linkedin": text(props.get("LinkedIn")),
            "photo": photo,
        })

    members.sort(key=lambda m: slug(m["name"]))
    for old in PHOTOS.glob("*"):
        if old.name not in keep_photos and old.suffix in (".webp", ".jpg", ".jpeg", ".png"):
            old.unlink()  # a member who left the list takes their photo with them
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(members, ensure_ascii=False, indent=2) + "\n")
    print(f"sync_notion: {len(members)} members written, {len(keep_photos)} with photos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
