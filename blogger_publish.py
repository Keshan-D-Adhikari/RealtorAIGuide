"""
Blogger (Blogspot) ekata posts upload karana module eka - Blogger API v3 + OAuth.

Mul paarа run karama browser eka open wela Google login ekak illanawa. Ita passe token.json save wenawa.

Test karanna:
    python blogger_publish.py          # login wela blog eka hoyagannawa
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_PATH = BASE_DIR / "client_secret.json"
TOKEN_PATH = BASE_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/blogger"]

load_dotenv(BASE_DIR / ".env")


def get_service():
    creds = None
    token_env = os.environ.get("GOOGLE_TOKEN_JSON")  # GitHub Actions wage cloud eke token.json content eka secret ekak widihata
    if token_env:
        creds = Credentials.from_authorized_user_info(json.loads(token_env), SCOPES)
        if not creds.valid:
            creds.refresh(Request())
        return build("blogger", "v3", credentials=creds)
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError(
                    "client_secret.json not found. Download the OAuth client (Desktop app) "
                    "from Google Cloud Console and put it in the blog folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("blogger", "v3", credentials=creds)


def get_blog_id(service) -> str:
    """.env eke BLOGGER_BLOG_ID thiyenawa nam eka, nathnam BLOGGER_URL eken hoyagannawa."""
    blog_id = os.environ.get("BLOGGER_BLOG_ID")
    if blog_id:
        return blog_id
    url = os.environ.get("BLOGGER_URL")
    if not url:
        raise ValueError("Set BLOGGER_URL (e.g. https://agentaihub.blogspot.com) in .env")
    return service.blogs().getByUrl(url=url).execute()["id"]


def upload_post(title: str, html: str, labels: list[str] | None = None, draft: bool = True) -> dict:
    """Post eka Blogger ekata upload karanawa. draft=True nam publish wenne na, oya check karala publish karanna."""
    service = get_service()
    blog_id = get_blog_id(service)
    body = {"kind": "blogger#post", "title": title, "content": html}
    if labels:
        body["labels"] = labels[:5]
    return service.posts().insert(blogId=blog_id, body=body, isDraft=draft).execute()


if __name__ == "__main__":
    service = get_service()
    blog_id = get_blog_id(service)
    blog = service.blogs().get(blogId=blog_id).execute()
    print(f"Connected: {blog['name']} ({blog['url']})  id={blog_id}")
    print(f"Posts: {blog.get('posts', {}).get('totalItems', 0)}")
    sys.exit(0)
