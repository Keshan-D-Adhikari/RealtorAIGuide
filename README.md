# Auto Blog Writer (USA target)

Claude API use karala, USA readers la target karala SEO blog posts automatically liyana script eka.

## Wada karana widiha
1. `config.json` eke niche list eken ekak random pick karanawa.
2. Web search (US location) use karala dan US eke trending / search karana topic ekak hoyanawa.
3. ~1500 words SEO post ekak liyanawa: meta description, keywords, H2/H3, FAQ, Key Takeaways, source links.
4. `posts/` folder eke `.md` saha `.html` (SEO meta + schema.org) widihata save karanawa.
5. `published.json` eke record karanawa — eka topic eka dennam liyanne na.

## Setup (eka parak witharai)
1. https://console.anthropic.com eken API key ekak ganna.
2. `.env.example` copy karala `.env` kiyala name karala, key eka danna.
3. `config.json` eke blog name, author, niches oyata ona widihata wenas karanna.

## Run karanna
```bash
.venv/Scripts/python auto_blog.py
```
Options:
- `--count 3` — posts 3k
- `--niche "personal finance"` — niche eka select karanna
- `--topic "Best air fryers under $100"` — specific topic ekak
- `--no-research` — web search nathuwa (cheaper)

## Dashboard (React UI)
`start_dashboard.bat` double-click karanna, nathnam:
```bash
.venv/Scripts/python server.py
```
Browser eke http://127.0.0.1:5000 open karanna. Posts generate karanna, preview karanna, Blogger ekata draft upload karanna, settings wenas karanna puluwan.
UI eka wenas kaloth: `cd ui && npm run build`

## Daily automatic run (Windows Task Scheduler)
Me command eka PowerShell eke run karama hama dawasema ude 9ta post ekak liyanawa:
```bash
schtasks /Create /SC DAILY /ST 09:00 /TN "AutoBlogWriter" /TR "\"D:\my store\prsonal blog\run_blog.bat\""
```
Logs: `blog_log.txt`. Ain karanna: `schtasks /Delete /TN "AutoBlogWriter" /F`

## Note
- Publish karanna kalin post eka kiyawala check karanna (facts, links). Google AI content ekata penalty denne na, eth low-quality/inaccurate content ekata denawa.
- Cost: post ekakata approx $0.20–$0.60 (Claude Opus 5.5 + web search).
