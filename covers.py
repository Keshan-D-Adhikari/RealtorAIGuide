"""
Post ekakata blog eke colours walin branded cover image ekak hadana module eka (Pillow, 100% free, API key ona na).

Image eka covers/ folder eke save wenawa. GitHub workflow eka eka repo ekata commit karanawa,
e nisa raw.githubusercontent.com link eken Blogger post eke image eka penawa.

Test karanna:
    python covers.py "Best AI Tools for Real Estate Agents" "AI Tools"
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
COVERS_DIR = BASE_DIR / "covers"
REPO_RAW = "https://raw.githubusercontent.com/Keshan-D-Adhikari/RealtorAIGuide/main/covers"

W, H = 1200, 630
NAVY, TEAL, MINT = (15, 42, 74), (14, 124, 123), (94, 234, 212)

# Windows (local) saha Ubuntu (GitHub Actions) dekema thiyena fonts
BOLD_FONTS = ["segoeuib.ttf", "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
REGULAR_FONTS = ["segoeui.ttf", "arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def category_for(niche: str) -> str:
    n = niche.lower()
    if "staging" in n or "photo" in n:
        return "Virtual Staging"
    if "prompt" in n or "chatgpt" in n:
        return "ChatGPT Prompts"
    if "crm" in n or "lead" in n:
        return "AI CRM"
    return "AI Tools"


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=fnt) <= max_w:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def make_cover(title: str, category: str, slug: str) -> Path:
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):  # navy -> teal diagonal gradient
        for x in range(W):
            t = min(1.0, (x / W) * 0.6 + (y / H) * 0.4)
            px[x, y] = tuple(int(NAVY[i] + (TEAL[i] - NAVY[i]) * t) for i in range(3))

    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((820, -160, 1360, 380), outline=(255, 255, 255, 28), width=40)
    d.ellipse((960, 330, 1300, 670), outline=(94, 234, 212, 40), width=24)

    # Logo: diamond + blog nama
    d.polygon([(80, 76), (94, 62), (108, 76), (94, 90)], fill=MINT)
    d.text((122, 76), "RealtorAIGuide", font=font(BOLD_FONTS, 30), fill="white", anchor="lm")

    # Category pill
    pf = font(BOLD_FONTS, 24)
    pw = d.textlength(category, font=pf)
    d.rounded_rectangle((80, 150, 80 + pw + 40, 196), radius=23, fill=(94, 234, 212, 235))
    d.text((100, 173), category, font=pf, fill=NAVY, anchor="lm")

    # Title - line 3kata wadi nam font eka podi karanawa
    for size in (68, 60, 52, 46):
        tf = font(BOLD_FONTS, size)
        lines = wrap(d, title, tf, 900)
        if len(lines) <= 3:
            break
    lines = lines[:3]
    y = 240
    for line in lines:
        d.text((80, y), line, font=tf, fill="white")
        y += int(size * 1.18)

    d.text((80, H - 60), "realtoraiguide.blogspot.com", font=font(REGULAR_FONTS, 24), fill=(255, 255, 255, 190), anchor="lm")

    COVERS_DIR.mkdir(exist_ok=True)
    path = COVERS_DIR / f"{slug}.jpg"
    img.save(path, "JPEG", quality=88, optimize=True)
    return path


def cover_html(title: str, niche: str, slug: str) -> str:
    """Cover eka hadala post eke mulata danna <img> HTML eka denawa."""
    make_cover(title, category_for(niche), slug)
    alt = title.replace('"', "&quot;")
    return f'<p><img src="{REPO_RAW}/{slug}.jpg" alt="{alt}" width="1200" height="630" style="width:100%;height:auto;border-radius:12px"/></p>\n'


if __name__ == "__main__":
    p = make_cover(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "AI Tools", "test-cover")
    print(p)
