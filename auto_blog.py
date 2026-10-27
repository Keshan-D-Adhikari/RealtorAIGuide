"""
Auto Blog Writer - USA audience target karala SEO blog posts automatically generate karana script eka.

Usage:
    python auto_blog.py                      # config.json eke niche eken trending topic ekak hoyala post 1k liyanawa
    python auto_blog.py --count 3            # posts 3k
    python auto_blog.py --topic "Best budget air fryers 2026"
    python auto_blog.py --niche "personal finance" --no-research
"""

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import anthropic
import httpx
import markdown
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
HISTORY_PATH = BASE_DIR / "published.json"

load_dotenv(BASE_DIR / ".env")

MODEL = "claude-opus-5-5"

# Server-side refusal fallback: model eka decline kaloth API eka automatically wena model ekakin retry karanawa
FALLBACK_BETA = "server-side-fallback-2026-07-01"

US_LOCATION = {
    "type": "approximate",
    "country": "US",
    "region": "California",
    "city": "Los Angeles",
    "timezone": "America/Los_Angeles",
}


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_history() -> list:
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: list) -> None:
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    return re.sub(r"[\s-]+", "-", text).strip("-")[:80]


def text_of(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


def run_stream(client: anthropic.Anthropic, **params):
    """Streaming request ekak yawala final message eka denawa. Web search pause_turn awoth continue karanawa."""
    messages = list(params.pop("messages"))
    for _ in range(5):
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            messages=messages,
            **params,
        ) as stream:
            message = stream.get_final_message()

        if message.stop_reason == "refusal":
            raise RuntimeError(f"Model refused the request: {message.stop_details}")
        if message.stop_reason != "pause_turn":
            return message
        messages.append({"role": "assistant", "content": message.content})
    raise RuntimeError("Too many pause_turn continuations")


class ClaudeLLM:
    """Anthropic Claude (paid)."""

    def __init__(self, cfg: dict):
        self.client = anthropic.Anthropic()
        self.cfg = cfg

    def ask(self, prompt: str, system: str | None = None, search: bool = False, effort: str = "medium") -> str:
        params = {"output_config": {"effort": effort}, "messages": [{"role": "user", "content": prompt}]}
        if system:
            params["system"] = system
        if search:
            params["tools"] = [{
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 6,
                "user_location": US_LOCATION,
            }]
        message = run_stream(self.client, **params)
        if message.stop_reason == "max_tokens":
            print("  ! Warning: response was cut off at max_tokens", file=sys.stderr)
        return text_of(message)


class GeminiLLM:
    """Google Gemini (free tier eka use karanna puluwan)."""

    def __init__(self, cfg: dict):
        from google import genai

        self.genai = genai
        # Request ekak hira unoth (response ekak nathuwa) paya ganan inne nathuwa 3 min walin ilaga model ekata yanawa
        self.client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=genai.types.HttpOptions(timeout=180_000),
        )
        first = cfg.get("gemini_model") or self.pick_model()
        # Ekak busy (503) hari quota iwara (429) unoth anith free models walata maru wenawa
        self.models = [first] + [m for m in cfg.get("gemini_fallback_models", []) if m != first]
        # Google Search grounding free key ekata quota na (429), e nisa default eka off
        self.search_allowed = cfg.get("gemini_search", False)
        print(f"  Using Gemini models: {', '.join(self.models)}")

    def pick_model(self) -> str:
        """Free tier eke thiyena aluthma 'flash' text model eka automatically thoragannawa."""
        best, best_ver = None, -1.0
        for m in self.client.models.list():
            name = m.name.removeprefix("models/")
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" not in actions:
                continue
            if not re.fullmatch(r"gemini-\d+(\.\d+)?-flash", name):  # lite / image / tts / preview walata yanne na
                continue
            ver = float(re.search(r"\d+(\.\d+)?", name).group())
            if ver > best_ver:
                best, best_ver = name, ver
        if not best:
            raise RuntimeError('No Gemini flash model found. Set "gemini_model" in config.json.')
        return best

    def ask(self, prompt: str, system: str | None = None, search: bool = False, effort: str = "medium") -> str:
        from google.genai import errors, types

        tools = [types.Tool(google_search=types.GoogleSearch())] if search and self.search_allowed else None
        last_error = None
        for round_ in range(3):
            for model in self.models:
                try:
                    resp = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(system_instruction=system, tools=tools),
                    )
                    if resp.text:
                        return resp.text
                except errors.APIError as e:
                    last_error = e
                    if tools and e.code in (400, 403, 429):
                        print("  Google Search grounding not available on free key, continuing without it.", file=sys.stderr)
                        tools = None
                        self.search_allowed = False
                    elif e.code == 404:  # model eka ain karala (retired) - eka list eken ain karala ilaga ekata yanawa
                        print(f"  {model} no longer available (404), skipping it.", file=sys.stderr)
                        self.models.remove(model)
                        if not self.models:
                            raise RuntimeError(f"Gemini API error {e.code}: {e.message}") from e
                    elif e.code in (429, 500, 503):
                        print(f"  {model} busy/limited ({e.code}), trying next model...", file=sys.stderr)
                    else:
                        raise RuntimeError(f"Gemini API error {e.code}: {e.message}") from e
                except (httpx.HTTPError, ConnectionError) as e:  # server eka connection eka drop kaloth
                    last_error = e
                    print(f"  {model} connection dropped, trying next model...", file=sys.stderr)
            if self.groq and round_ == 0:  # Gemini okkoma busy nam inna nathuwa kelinma Groq ekata yanawa
                break
            print("  All models busy, waiting 60s before retrying...", file=sys.stderr)
            time.sleep(60)
        if self.groq:
            print("  Gemini busy, writing with Groq instead...", file=sys.stderr)
            return self.groq.ask(prompt, system=system)
        raise RuntimeError(f"Gemini unavailable right now ({getattr(last_error, 'code', '?')}). Try again later.")


class GroqLLM:
    """Groq free API (card ona na) - Gemini busy unoth backup eka."""

    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, cfg: dict):
        self.key = os.environ["GROQ_API_KEY"]
        self.models = cfg.get("groq_models", ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3-32b"])

    def ask(self, prompt: str, system: str | None = None, **_) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        last = None
        for round_ in range(3):
            for model in self.models:
                try:
                    r = httpx.post(
                        self.URL,
                        headers={"Authorization": f"Bearer {self.key}"},
                        json={"model": model, "messages": messages, "max_tokens": 8000},
                        timeout=180,
                    )
                except httpx.HTTPError as e:
                    last = e
                    continue
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
                last = f"{r.status_code} {r.text[:200]}"
                print(f"  Groq {model} failed ({r.status_code}), trying next...", file=sys.stderr)
            time.sleep(60)
        raise RuntimeError(f"Groq unavailable right now ({last}). Try again later.")


def make_llm(cfg: dict):
    if cfg.get("ai_provider", "gemini") == "claude":
        return ClaudeLLM(cfg)
    llm = GeminiLLM(cfg)
    llm.groq = GroqLLM(cfg) if os.environ.get("GROQ_API_KEY") else None
    return llm


def research_topic(llm, niche: str, history: list, cfg: dict) -> dict:
    """Web search use karala US audience ekata trending, search-demand thiyena topic ekak hoyanawa."""
    recent = [h["title"] for h in history[-50:]]
    today = dt.date.today().isoformat()
    prompt = f"""Today is {today}. I run a blog for readers in the United States.

Niche: {niche}

Use web search to find what US readers are searching for right now in this niche
(seasonal events, new product launches, news, rising questions). Pick ONE blog post idea that:
- has clear search intent from US readers (informational or buying-guide),
- is specific and long-tail enough for a small blog to rank,
- is NOT a duplicate of any of these already-published titles: {json.dumps(recent)}

Reply with ONLY a JSON object in a ```json code block with these keys:
"title" (SEO title, under 65 chars), "primary_keyword", "secondary_keywords" (list of 5-8),
"search_intent", "angle" (one sentence on what makes this post useful),
"key_facts" (list of up-to-date facts/figures you found, each with its source URL)."""

    if not getattr(llm, "search_allowed", True):
        prompt = prompt.replace("Use web search to find what US readers are searching for right now",
                                "Based on your knowledge, pick what US readers commonly search for")
        prompt += ("\nYou have NO web access: do not invent statistics, prices, dates or URLs. "
                   'Set "key_facts" to an empty list unless you are certain of a fact.')
    raw = llm.ask(prompt, search=True, effort=cfg.get("research_effort", "medium"))
    match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.S) or re.search(r"(\{.*\})", raw, re.S)
    if not match:
        raise ValueError(f"Could not parse topic JSON from research step:\n{raw[:1000]}")
    return json.loads(match.group(1))


def write_post(llm, topic: dict, cfg: dict) -> str:
    """Topic eka anuwa full SEO blog post eka Markdown (YAML front matter ekka) liyanawa."""
    system = f"""You are an experienced American blogger and SEO content writer.
Write in natural, conversational US English (American spelling, USD, imperial units, US examples).
Blog name: {cfg.get("blog_name", "My Blog")}. Author: {cfg.get("author", "Admin")}.
Tone: {cfg.get("tone", "friendly, helpful, trustworthy")}.

Follow Google's helpful-content guidelines: original insight, practical steps, no fluff, no keyword stuffing,
no fabricated statistics. Only state figures that appear in the provided research facts; otherwise speak generally.
Do not quote specific prices, plan names, discounts or release dates for products; tell readers to check the
vendor's website for current pricing. Only recommend well-established products you are confident still exist."""
    if cfg.get("editor_passes"):
        system += "\n\nWriting style guidelines (follow all of them while writing):\n" + "\n".join(
            f"- {p.replace('the following text', 'your text').replace('the following content', 'your content')}"
            for p in cfg["editor_passes"]
        )

    words = cfg.get("word_count", 1500)
    prompt = f"""Write a complete blog post based on this research brief:

{json.dumps(topic, indent=2, ensure_ascii=False)}

Requirements:
- About {words} words.
- Output ONLY Markdown, starting with YAML front matter exactly like:
---
title: "..."
meta_description: "... (150-160 chars)"
slug: "..."
primary_keyword: "..."
keywords: ["...", "..."]
date: "{dt.date.today().isoformat()}"
author: "{cfg.get("author", "Admin")}"
---
- Then: an engaging intro (primary keyword in the first 100 words), H2/H3 sections,
  at least one bullet list or table, a "Key Takeaways" box, an FAQ section with 4-5 questions
  (People-Also-Ask style), and a short conclusion with a call to action.
- Where you use a fact from the brief, cite it inline as a Markdown link to its source.
- Do not include an H1 (the title comes from front matter)."""

    md = llm.ask(prompt, system=system, effort=cfg.get("writing_effort", "high")).strip()
    md = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", md)  # model eka code fence ekak dammoth ain karanawa
    return md


EDIT_RULES = """Formatting rules (must follow):
- Return ONLY the edited Markdown body. No preface, no notes, no code fences.
- Keep every heading (## / ###), list, table, FAQ question and link (same URLs) in place.
- Do not add facts, statistics, product names, prices or links that are not already in the text.
- Keep it in US English."""


def edit_post(llm, body: str, cfg: dict) -> str:
    """Oya dunna editor instructions use karala post body eka natural, human widihata rewrite karanawa."""
    passes = cfg.get("editor_passes") or []
    if not cfg.get("editor_enabled", True) or not passes:
        return body

    if cfg.get("editor_mode", "combined") == "sequential":
        steps = passes  # instruction ekin ekata wenama call (free tier eke rate limit ikmanata iwara wenna puluwan)
    else:
        steps = ["Apply ALL of these editing instructions together in one careful rewrite:\n\n"
                 + "\n\n".join(f"{i}. {p}" for i, p in enumerate(passes, 1))]

    for i, instruction in enumerate(steps, 1):
        print(f"  Editing pass {i}/{len(steps)}...")
        edited = llm.ask(f"{instruction}\n\n{EDIT_RULES}\n\nText:\n\n{body}",
                         effort=cfg.get("writing_effort", "high")).strip()
        edited = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", edited)
        # Edit eka headings nathi kaloth hari godak keti kaloth original eka thiyagannawa
        if edited.count("## ") < body.count("## ") * 0.8 or len(edited) < len(body) * 0.6:
            print("  ! Edit changed the structure too much, keeping previous version", file=sys.stderr)
            continue
        body = edited
    return body


def parse_front_matter(md: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", md, re.S)
    if not m:
        return {}, md
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            try:
                meta[k.strip()] = json.loads(v)
            except json.JSONDecodeError:
                meta[k.strip()] = v.strip('"')
    return meta, m.group(2)


def to_html(meta: dict, body_md: str, cfg: dict) -> str:
    body = markdown.markdown(body_md, extensions=["tables", "fenced_code"])
    title = meta.get("title", "")
    desc = meta.get("meta_description", "")
    keywords = ", ".join(meta.get("keywords", [])) if isinstance(meta.get("keywords"), list) else ""
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": desc,
        "datePublished": meta.get("date", ""),
        "author": {"@type": "Person", "name": meta.get("author", "")},
        "inLanguage": "en-US",
    }
    return f"""<!doctype html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{keywords}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<script type="application/ld+json">{json.dumps(schema)}</script>
<style>
body{{max-width:760px;margin:0 auto;padding:24px 16px;font:18px/1.7 Georgia,serif;color:#222;background:#fff}}
h1,h2,h3{{font-family:system-ui,sans-serif;line-height:1.3}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}
a{{color:#0b5cad}}
</style>
</head>
<body>
<article>
<h1>{title}</h1>
<p><small>By {meta.get("author", "")} &middot; {meta.get("date", "")}</small></p>
{body}
</article>
</body>
</html>
"""


def generate_one(llm, cfg: dict, history: list, niche: str | None, topic_title: str | None, research: bool) -> Path:
    niche = niche or random.choice(cfg["niches"])
    print(f"\n==> Niche: {niche}")

    if topic_title:
        topic = {"title": topic_title, "primary_keyword": topic_title.lower(), "niche": niche}
    elif research:
        print("  Researching trending US topics (web search)...")
        topic = research_topic(llm, niche, history, cfg)
    else:
        topic = {"title": f"Pick a specific, high-search-intent topic for US readers in: {niche}"}
    print(f"  Topic: {topic.get('title')}")

    print("  Writing post...")
    md = write_post(llm, topic, cfg)
    meta, body = parse_front_matter(md)
    edited = edit_post(llm, body, cfg)
    if edited != body:
        md = md.replace(body, edited, 1)
        body = edited

    check_report = []
    if cfg.get("fact_check", True):
        from fact_check import fact_check

        print("  Fact-checking products against their official websites...")
        md, check_report = fact_check(llm, md, body)
        meta, body = parse_front_matter(md)

    date = dt.date.today().isoformat()
    slug = slugify(meta.get("slug") or meta.get("title") or topic.get("title", "post"))

    if cfg.get("covers", True):  # free branded cover image (Pillow) - post eke mulata
        from covers import cover_html

        cover = cover_html(meta.get("title", topic.get("title", "")), niche, slug)
        md = md.replace(body, cover + "\n" + body, 1)
        body = cover + "\n" + body
        print(f"  Cover image: covers/{slug}.jpg")

    image = {"html": "", "local_file": None}
    if cfg.get("images", True):
        from images import featured_image

        image = featured_image(meta, slug, cfg)
        if image["html"]:
            md = md.replace(body, image["html"] + "\n" + body, 1)
            body = image["html"] + "\n" + body
    out_dir = BASE_DIR / "posts"
    out_dir.mkdir(exist_ok=True)
    md_path = out_dir / f"{date}-{slug}.md"
    md_path.write_text(md, encoding="utf-8")
    if cfg.get("export_html", True):
        (out_dir / f"{date}-{slug}.html").write_text(to_html(meta, body, cfg), encoding="utf-8")

    entry = {
        "date": date,
        "niche": niche,
        "title": meta.get("title", topic.get("title")),
        "file": md_path.name,
        "ai_image": image["local_file"],
        "fact_check": [{k: r[k] for k in ("name", "url", "status", "verified")} for r in check_report],
    }

    if cfg.get("blogger_upload", False):
        from blogger_publish import upload_post

        draft = cfg.get("blogger_mode", "draft") != "publish"
        print(f"  Uploading to Blogger ({'draft' if draft else 'publish'})...")
        body_html = markdown.markdown(body, extensions=["tables", "fenced_code"])
        labels = cfg.get("blogger_labels") or [niche]
        post = upload_post(entry["title"], body_html, labels, draft=draft)
        entry["blogger_id"] = post["id"]
        entry["blogger_url"] = post.get("url", "")
        print(f"  Blogger post id: {post['id']}")

    history.append(entry)
    save_history(history)
    print(f"  Saved: {md_path}")
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-generate USA-targeted SEO blog posts with Gemini or Claude")
    parser.add_argument("--count", type=int, default=None, help="Number of posts to generate")
    parser.add_argument("--niche", help="Override niche (otherwise random from config.json)")
    parser.add_argument("--topic", help="Write about this exact topic (skips research)")
    parser.add_argument("--no-research", action="store_true", help="Skip web search topic research")
    args = parser.parse_args()

    cfg = load_config()
    key_name = "ANTHROPIC_API_KEY" if cfg.get("ai_provider", "gemini") == "claude" else "GEMINI_API_KEY"
    if not os.environ.get(key_name):
        print(f"ERROR: {key_name} not set. Add it to .env or Windows environment variables.", file=sys.stderr)
        return 1

    history = load_history()
    llm = make_llm(cfg)
    count = args.count or cfg.get("posts_per_run", 1)

    failures = 0
    for i in range(count):
        try:
            generate_one(llm, cfg, history, args.niche, args.topic, not args.no_research)
        except anthropic.AuthenticationError:
            print("ERROR: Invalid or missing ANTHROPIC_API_KEY. Put it in the .env file.", file=sys.stderr)
            return 1
        except anthropic.RateLimitError:
            print("ERROR: Rate limited. Try again later.", file=sys.stderr)
            return 1
        except anthropic.APIStatusError as e:
            print(f"ERROR: API error {e.status_code}: {e.message}", file=sys.stderr)
            failures += 1
        except anthropic.APIConnectionError:
            print("ERROR: Network error. Check your internet connection.", file=sys.stderr)
            failures += 1
        except (ValueError, RuntimeError, OSError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            failures += 1

    print(f"\nDone. {count - failures}/{count} posts generated.")
    return 1 if failures == count else 0


if __name__ == "__main__":
    sys.exit(main())
