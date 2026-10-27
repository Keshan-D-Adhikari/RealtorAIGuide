@echo off
cd /d "%~dp0"
if not exist token.json (echo token.json not found. Run: .venv\Scripts\python.exe blogger_publish.py & pause & exit /b 1)
clip < token.json
echo Blogger token copied to clipboard. Paste it into the GOOGLE_TOKEN_JSON secret on GitHub.
pause
