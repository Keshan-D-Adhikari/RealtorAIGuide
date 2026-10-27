"""
Gemini API key eka .env ekata save karala test karana podi tool eka.
set_key.bat double-click karala key eka paste karanna (screen eke penne na).
"""

from getpass import getpass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
NAME = "GEMINI_API_KEY"

value = getpass(f"Paste your new {NAME} and press Enter (it will not be shown): ").strip()
if not value or any(c in value for c in " =\r\n"):
    raise SystemExit("No valid key entered. Nothing changed.")

lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
lines = [l for l in lines if not l.startswith(f"{NAME}=")]
lines.insert(0, f"{NAME}={value}")
ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Saved to {ENV_PATH}")

from google import genai

try:
    reply = genai.Client(api_key=value).models.generate_content(
        model="gemini-flash-latest", contents="Reply with just OK"
    ).text.strip()
    print(f"Key test: {reply}  -> the key works.")
except Exception as e:  # key eka waradi nam hari Google busy nam
    print(f"Key test failed: {e}")
