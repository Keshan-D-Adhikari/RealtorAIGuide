"""
Dashboard backend - React UI eka me API eka hараha script eka control karanawa.

    python server.py      ->  http://localhost:5000
"""

import json
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import markdown
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"
DIST_DIR = BASE_DIR / "ui" / "dist"
CONFIG_PATH = BASE_DIR / "config.json"
HISTORY_PATH = BASE_DIR / "published.json"

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=None)
jobs: dict[str, dict] = {}


def read_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


@app.get("/api/status")
def status():
    cfg = read_json(CONFIG_PATH, {})
    provider = cfg.get("ai_provider", "gemini")
    key_name = "ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY"
    return jsonify({
        "provider": provider,
        "ai_key": bool(os.environ.get(key_name)),
        "images": bool(cfg.get("images", False)),
        "pexels_key": bool(os.environ.get("PEXELS_API_KEY")),
        "blogger_connected": (BASE_DIR / "token.json").exists(),
        "blog_url": os.environ.get("BLOGGER_URL", ""),
        "running": any(j["status"] == "running" for j in jobs.values()),
    })


@app.get("/api/config")
def get_config():
    return jsonify(read_json(CONFIG_PATH, {}))


@app.put("/api/config")
def put_config():
    data = request.get_json(force=True)
    if not isinstance(data, dict) or not data.get("niches"):
        abort(400, "config must include at least one niche")
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return jsonify(data)


@app.get("/api/posts")
def list_posts():
    history = {h["file"]: h for h in read_json(HISTORY_PATH, [])}
    posts = []
    for f in sorted(POSTS_DIR.glob("*.md"), reverse=True) if POSTS_DIR.exists() else []:
        h = history.get(f.name, {})
        posts.append({
            "file": f.name,
            "title": h.get("title", f.stem),
            "date": h.get("date", f.name[:10]),
            "niche": h.get("niche", ""),
            "blogger_id": h.get("blogger_id"),
            "blogger_url": h.get("blogger_url"),
        })
    return jsonify(posts)


def safe_post_path(name: str) -> Path:
    path = (POSTS_DIR / name).resolve()
    if path.parent != POSTS_DIR.resolve() or path.suffix != ".md" or not path.exists():
        abort(404)
    return path


@app.get("/api/posts/<name>")
def get_post(name):
    md = safe_post_path(name).read_text(encoding="utf-8")
    from auto_blog import parse_front_matter

    meta, body = parse_front_matter(md)
    return jsonify({"meta": meta, "markdown": md, "html": markdown.markdown(body, extensions=["tables", "fenced_code"])})


@app.post("/api/posts/<name>/upload")
def upload(name):
    from auto_blog import parse_front_matter
    from blogger_publish import upload_post

    path = safe_post_path(name)
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
    cfg = read_json(CONFIG_PATH, {})
    html = markdown.markdown(body, extensions=["tables", "fenced_code"])
    post = upload_post(meta.get("title", path.stem), html, cfg.get("blogger_labels"), draft=True)

    history = read_json(HISTORY_PATH, [])
    for h in history:
        if h.get("file") == name:
            h["blogger_id"], h["blogger_url"] = post["id"], post.get("url", "")
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return jsonify({"id": post["id"], "url": post.get("url", "")})


def run_job(job_id: str, args: list[str]):
    job = jobs[job_id]
    proc = subprocess.Popen(
        [sys.executable, "-u", "-W", "ignore", str(BASE_DIR / "auto_blog.py"), *args],
        cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
    )
    for line in proc.stdout:
        job["log"].append(line.rstrip())
    proc.wait()
    job["status"] = "done" if proc.returncode == 0 else "failed"


@app.post("/api/generate")
def generate():
    if any(j["status"] == "running" for j in jobs.values()):
        abort(409, "A job is already running")
    data = request.get_json(force=True) or {}
    args = ["--count", str(max(1, min(int(data.get("count", 1)), 5)))]
    if data.get("niche"):
        args += ["--niche", data["niche"]]
    if data.get("topic"):
        args += ["--topic", data["topic"]]
    if data.get("research") is False:
        args.append("--no-research")
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {"id": job_id, "status": "running", "log": []}
    threading.Thread(target=run_job, args=(job_id, args), daemon=True).start()
    return jsonify(jobs[job_id])


@app.get("/api/jobs/<job_id>")
def get_job(job_id):
    if job_id not in jobs:
        abort(404)
    return jsonify(jobs[job_id])


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path):
    if path and (DIST_DIR / path).is_file():
        return send_from_directory(DIST_DIR, path)
    if not (DIST_DIR / "index.html").exists():
        return "UI not built. Run: cd ui && npm install && npm run build", 503
    return send_from_directory(DIST_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
