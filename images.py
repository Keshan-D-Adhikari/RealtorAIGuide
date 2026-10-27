"""
Post ekata featured image eka hoyana / hadana module eka.

1. Pexels (free stock photos) - PEXELS_API_KEY thiyenawa nam, image eka post eke udinma automatically danawa.
2. Gemini image generation - free tier eke wada karoth posts/images/ folder eke save karanawa.
   Blogger API eken image files upload karanna ba, e nisa eka draft eka edit karaddi oya manually upload karanna.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "posts" / "images"


def pexels_image(query: str) -> dict | None:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "per_page": 5, "orientation": "landscape"}
    )
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "auto-blog/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            photos = json.load(r).get("photos", [])
    except Exception as e:  # network / quota errors - image nathuwa post eka yanna denawa
        print(f"  Pexels error: {e}", file=sys.stderr)
        return None
    if not photos:
        return None
    p = photos[0]
    return {
        "url": p["src"]["large2x"],
        "alt": p.get("alt") or query,
        "credit": p["photographer"],
        "credit_url": p["photographer_url"],
        "source_url": p["url"],
    }


def gemini_image(prompt: str, slug: str, cfg: dict) -> Path | None:
    if not os.environ.get("GEMINI_API_KEY") or not cfg.get("gemini_images", True):
        return None
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = cfg.get("gemini_image_model")
    if not model:
        names = [m.name.removeprefix("models/") for m in client.models.list()]
        candidates = sorted(n for n in names if re.match(r"gemini-.*flash.*image", n))
        if not candidates:
            return None
        model = candidates[-1]
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
    except errors.APIError as e:
        print(f"  Gemini image not available on this key ({e.code}). Skipping AI image.", file=sys.stderr)
        return None
    for part in resp.candidates[0].content.parts if resp.candidates else []:
        if part.inline_data and part.inline_data.data:
            IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            ext = (part.inline_data.mime_type or "image/png").split("/")[-1]
            path = IMAGES_DIR / f"{slug}.{ext}"
            path.write_bytes(part.inline_data.data)
            return path
    return None


def featured_image(meta: dict, slug: str, cfg: dict) -> dict:
    """Returns {'html': <figure> to put at top of post or '', 'local_file': path or None}."""
    keyword = meta.get("primary_keyword") or meta.get("title", "")
    result = {"html": "", "local_file": None}

    photo = pexels_image(cfg.get("image_query_prefix", "real estate agent") + " " + keyword.split(" for ")[0])
    if not photo:
        photo = pexels_image(cfg.get("image_query_prefix", "real estate agent"))
    if photo:
        result["html"] = (
            f'<figure><img src="{photo["url"]}" alt="{escape(meta.get("title", photo["alt"]))}" '
            f'width="1200" loading="eager"/>'
            f'<figcaption>Photo by <a href="{photo["credit_url"]}" rel="nofollow">{escape(photo["credit"])}</a> '
            f'on <a href="{photo["source_url"]}" rel="nofollow">Pexels</a></figcaption></figure>\n'
        )
        print(f"  Featured image: Pexels photo by {photo['credit']}")

    ai_prompt = (
        f"A clean, modern, professional blog header illustration for an article titled "
        f"\"{meta.get('title', keyword)}\". Theme: real estate agents using AI tools. "
        f"Flat design, navy and teal colors, no text, 16:9."
    )
    path = gemini_image(ai_prompt, slug, cfg)
    if path:
        result["local_file"] = str(path)
        print(f"  AI image saved: {path} (upload it in the Blogger editor if you prefer it)")
    return result
