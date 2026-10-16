#!/usr/bin/env python3
"""Fetch the public-domain engravings the plates are built from.

Every file is looked up on Wikimedia Commons through the API, its licence is
read from the API's own extmetadata and checked against an allowlist, and
only then is a scaled rendition downloaded. Nothing here invents a URL: the
download URL is whatever the API returns. Results (with attribution) are
recorded in sources.json next to the images.

usage: sources.py OUT_DIR
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "riceforge-plates/1.0 (personal desktop wallpaper; non-commercial)"}
API = "https://commons.wikimedia.org/w/api.php"
ALLOWED = {"public domain", "no restrictions", "cc0", "pd"}

# slug -> Commons file title
FILES = {
    "flammarion": "File:Flammarion.jpg",
    "nasmyth-crater": "File:Normal lunar crater - J. Nasmyth. LCCN2001700463.jpg",
    "vesalius-musculorum": "File:Tertia musculorum tabula (37053621276).jpg",
    "dore-empyrean": "File:Paradiso Canto 31 (no caption).jpg",
    "fludd-macrocosm": "File:UtriusqueCosmiMacrocosm.png",
}


def get(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "sources.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    for slug, title in FILES.items():
        if slug in meta and (out / meta[slug]["file"]).exists():
            print(f"have {slug}")
            continue
        q = urllib.parse.urlencode({
            "action": "query", "format": "json", "titles": title, "prop": "imageinfo",
            "iiprop": "url|size|extmetadata", "iiurlwidth": 2600,
        })
        page = next(iter(json.loads(get(f"{API}?{q}"))["query"]["pages"].values()))
        if "imageinfo" not in page:
            print(f"skip {slug}: not found on Commons")
            continue
        ii = page["imageinfo"][0]
        md = ii.get("extmetadata", {})
        lic = strip_html(md.get("LicenseShortName", {}).get("value", ""))
        if lic.lower() not in ALLOWED:
            print(f"skip {slug}: licence '{lic}' not in allowlist")
            continue
        url = ii.get("thumburl") or ii["url"]
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".jpg"
        fname = f"{slug}{ext}"
        (out / fname).write_bytes(get(url))
        meta[slug] = {
            "file": fname,
            "title": title.removeprefix("File:"),
            "artist": strip_html(md.get("Artist", {}).get("value", "")),
            "date": strip_html(md.get("DateTimeOriginal", {}).get("value", "")),
            "licence": lic,
            "page": ii.get("descriptionurl", ""),
            "original_size": [ii.get("width"), ii.get("height")],
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        print(f"got  {slug}: {lic} · {meta[slug]['artist'][:60]}")
        time.sleep(2)


if __name__ == "__main__":
    main()
