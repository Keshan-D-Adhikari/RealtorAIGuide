"""
Post eke thiyena products / tools thama thiyenawada kiyala free widihata check karana module eka.

1. Gemini ta post eke thiyena product names saha official website URL list ekak illanawa.
2. Hama URL ekakatama HTTP request ekak yawala, site eka live da, page eke product nama thiyenawada balanawa.
3. Verify nowechcha products post eken ain karanawa, verify wechcha ewata official site link ekak danawa.
"""

import json
import re
import sys
import urllib.request
from html import unescape

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def fetch_text(url: str) -> tuple[int, str, str]:
    """(status, final_url, lowercase page text)"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read(600_000).decode("utf-8", "ignore")
            return r.status, r.geturl(), unescape(re.sub(r"<[^>]+>", " ", html)).lower()
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception:
        return 0, url, ""


def name_tokens(name: str) -> list[str]:
    # "Ylopo (Raiya AI)" -> ["ylopo"] ; "Tidio" -> ["tidio"]
    main = re.split(r"[(\-–:]", name)[0]
    return [t for t in re.findall(r"[a-z0-9]+", main.lower()) if len(t) > 2 and t not in {"the", "app", "for"}]


def verify_product(p: dict) -> dict:
    status, final_url, text = fetch_text(p["url"])
    tokens = name_tokens(p["name"])
    host = re.sub(r"^https?://(www\.)?", "", final_url).split("/")[0].lower()
    name_found = bool(tokens) and any(t in text or t in host for t in tokens)
    ok = status in (200, 301, 302, 403) and (name_found or status == 403)  # 403 = bot block, site eka live
    return {**p, "status": status, "final_url": final_url, "verified": ok}


def extract_products(llm, body: str) -> list[dict]:
    prompt = f"""List every software product, app, tool or company that this blog post recommends or reviews.
For each give its official homepage URL.

Reply with ONLY a JSON array in a ```json block, like:
[{{"name": "Tidio", "url": "https://www.tidio.com"}}]
If you are not sure a product still exists or of its URL, still include it with your best guess.

Post:
{body}"""
    raw = llm.ask(prompt)
    m = re.search(r"```json\s*(\[.*?\])\s*```", raw, re.S) or re.search(r"(\[.*\])", raw, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    return [i for i in items if isinstance(i, dict) and i.get("name") and str(i.get("url", "")).startswith("http")]


def fact_check(llm, md: str, body: str) -> tuple[str, list[dict]]:
    """Returns (updated full markdown, report)."""
    products = extract_products(llm, body)
    if not products:
        print("  Fact-check: no products found to verify")
        return md, []

    report = [verify_product(p) for p in products]
    good = [r for r in report if r["verified"]]
    bad = [r for r in report if not r["verified"]]
    for r in report:
        mark = "OK " if r["verified"] else "BAD"
        print(f"  Fact-check {mark} {r['name']} -> {r['url']} ({r['status']})")

    instructions = []
    if bad:
        names = ", ".join(r["name"] for r in bad)
        instructions.append(
            f"Remove every section, list item, table row and mention of these products, because they could not be "
            f"verified as currently available: {names}. Renumber lists, and update any number in the title, "
            f"meta_description, slug and headings (e.g. '5 Best' -> '4 Best') so counts stay correct."
        )
    if good:
        # Redirect wela ena URL eke ad tracking / country pages enna puluwan, e nisa clean homepage eka link karanawa
        links = "\n".join(f"- {r['name']}: {r['url'].split('?')[0]}" for r in good)
        instructions.append(
            "Link the FIRST mention of each of these products in the body to its official site (Markdown link), "
            f"and do not add any other new links:\n{links}"
        )

    prompt = (
        "Edit this Markdown blog post (including its YAML front matter).\n\n"
        + "\n\n".join(instructions)
        + "\n\nChange nothing else. Keep all other headings, wording and the front matter format. "
        "Return ONLY the full edited Markdown, starting with the --- front matter. No code fences.\n\n"
        + md
    )
    edited = llm.ask(prompt).strip()
    edited = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", edited)
    if not edited.startswith("---") or len(edited) < len(md) * 0.5:
        print("  ! Fact-check edit looked wrong, keeping post unchanged (check products manually)", file=sys.stderr)
        return md, report
    return edited, report
