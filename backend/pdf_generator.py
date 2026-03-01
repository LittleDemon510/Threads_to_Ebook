"""
pdf_generator.py — Threads Ebook PDF Generator

Layout (from template):
  1. Cover page (front)       — Book icon, title, username
  2. Profile page (header)    — Bio, location, followers, following
  3. Content pages            — Each post as a styled card
  4. Tail page                — Closing / stats summary
  5. Back cover               — Clean back page

Design: Clean book aesthetic, Threads-inspired dark accents
"""

import io
import os
import logging
import textwrap
from datetime import datetime
import requests

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import Color, black, white, HexColor
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame, KeepInFrame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ─── PAGE SIZE: A5 (book format) ──────────────────────────────────────────
PAGE_W, PAGE_H = A5           # 148mm x 210mm
MARGIN = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ─── COLOR PALETTE ────────────────────────────────────────────────────────
C_BLACK      = HexColor("#0a0a0a")
C_WHITE      = HexColor("#ffffff")
C_GRAY_DARK  = HexColor("#1a1a1a")
C_GRAY_MID   = HexColor("#555555")
C_GRAY_LIGHT = HexColor("#cccccc")
C_GRAY_BG    = HexColor("#f5f5f5")
C_ACCENT     = HexColor("#000000")
C_BORDER     = HexColor("#e0e0e0")
C_THREADS    = HexColor("#101010")


# ─── IMAGE DOWNLOAD HELPER ────────────────────────────────────────────────
def download_image(url: str, max_bytes: int = 5_000_000) -> bytes | None:
    """Download image from URL, return bytes or None on failure."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ThreadsEbook/1.0)",
            "Referer": "https://www.threads.net/"
        }
        resp = requests.get(url, headers=headers, timeout=8, stream=True)
        resp.raise_for_status()
        data = b""
        for chunk in resp.iter_content(8192):
            data += chunk
            if len(data) > max_bytes:
                return None   # Too large, skip
        return data
    except Exception as e:
        logger.warning(f"Failed to download image {url[:80]}: {e}")
        return None


def image_bytes_to_reportlab(img_data: bytes):
    """Convert raw image bytes to a PIL image and return path usable by ReportLab."""
    try:
        img = PILImage.open(io.BytesIO(img_data))
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.warning(f"Image processing failed: {e}")
        return None


# ─── CANVAS HELPERS ───────────────────────────────────────────────────────
def draw_rounded_rect(c, x, y, w, h, r=4*mm, fill_color=None, stroke_color=None, stroke_width=0.5):
    """Draw a rounded rectangle."""
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    else:
        c.setLineWidth(0)

    path = c.beginPath()
    path.moveTo(x + r, y)
    path.lineTo(x + w - r, y)
    path.arcTo(x + w - 2*r, y, x + w, y + 2*r, startAng=-90, extent=90)
    path.lineTo(x + w, y + h - r)
    path.arcTo(x + w - 2*r, y + h - 2*r, x + w, y + h, startAng=0, extent=90)
    path.lineTo(x + r, y + h)
    path.arcTo(x, y + h - 2*r, x + 2*r, y + h, startAng=90, extent=90)
    path.lineTo(x, y + r)
    path.arcTo(x, y, x + 2*r, y + 2*r, startAng=180, extent=90)
    path.close()

    if fill_color and stroke_color:
        c.drawPath(path, fill=1, stroke=1)
    elif fill_color:
        c.drawPath(path, fill=1, stroke=0)
    else:
        c.drawPath(path, fill=0, stroke=1)


def set_font(c, size, bold=False):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)


def centered_text(c, text, y, size=11, bold=False, color=None):
    if color:
        c.setFillColor(color)
    set_font(c, size, bold)
    c.drawCentredString(PAGE_W / 2, y, text)


def page_number(c, n, total):
    c.setFillColor(C_GRAY_MID)
    set_font(c, 8)
    c.drawCentredString(PAGE_W / 2, 7 * mm, f"{n} / {total}")


# ─── COVER PAGE ───────────────────────────────────────────────────────────
def draw_cover(c, profile):
    """Page 1 — Cover: black background, icon, title, username."""
    # Full black background
    c.setFillColor(C_BLACK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Thin white border inset
    c.setStrokeColor(HexColor("#2a2a2a"))
    c.setLineWidth(0.5)
    inset = 6 * mm
    c.rect(inset, inset, PAGE_W - 2*inset, PAGE_H - 2*inset, fill=0, stroke=1)

    # Book icon (use the uploaded PNG icon)
    icon_path = os.path.join(os.path.dirname(__file__), "icon16.png")
    if os.path.exists(icon_path):
        try:
            icon_size = 28 * mm
            icon_x = (PAGE_W - icon_size) / 2
            icon_y = PAGE_H * 0.55
            c.drawImage(icon_path, icon_x, icon_y, width=icon_size, height=icon_size,
                        mask="auto", preserveAspectRatio=True)
        except Exception:
            pass
    else:
        # Draw a simple "@ in circle" fallback
        cx, cy = PAGE_W / 2, PAGE_H * 0.60
        r = 14 * mm
        c.setFillColor(white)
        c.circle(cx, cy, r, fill=0, stroke=1)
        c.setStrokeColor(white)
        c.setLineWidth(1.5)
        set_font(c, 20, bold=True)
        c.setFillColor(white)
        c.drawCentredString(cx, cy - 3*mm, "@")

    # Title
    c.setFillColor(white)
    set_font(c, 22, bold=True)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.44, "Threads")
    set_font(c, 14, bold=False)
    c.setFillColor(C_GRAY_LIGHT)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.38, "Ebook")

    # Horizontal divider
    c.setStrokeColor(HexColor("#333333"))
    c.setLineWidth(0.5)
    c.line(MARGIN * 2, PAGE_H * 0.33, PAGE_W - MARGIN * 2, PAGE_H * 0.33)

    # Username
    c.setFillColor(white)
    set_font(c, 13, bold=True)
    username = "@" + profile.get("username", "user")
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.27, username)

    # Subtitle
    c.setFillColor(C_GRAY_MID)
    set_font(c, 8)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.21, "A collection of Threads posts")

    # Generation date at bottom
    c.setFillColor(HexColor("#333333"))
    set_font(c, 8)
    gen_date = datetime.now().strftime("%B %Y")
    c.drawCentredString(PAGE_W / 2, inset * 1.8, gen_date)


# ─── PROFILE PAGE ─────────────────────────────────────────────────────────
def draw_profile_page(c, profile, page_num, total_pages):
    """Page 2 — Profile: name, bio, location, followers, following."""
    # Light background
    c.setFillColor(C_WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    y = PAGE_H - MARGIN

    # Header band
    c.setFillColor(C_BLACK)
    c.rect(0, PAGE_H - 22*mm, PAGE_W, 22*mm, fill=1, stroke=0)

    c.setFillColor(white)
    set_font(c, 14, bold=True)
    c.drawString(MARGIN, PAGE_H - 13*mm, "@" + profile.get("username", ""))

    c.setFillColor(C_GRAY_LIGHT)
    set_font(c, 8)
    c.drawString(MARGIN, PAGE_H - 19*mm, "Threads Profile")

    y = PAGE_H - 30*mm

    # Display name
    display = profile.get("display_name", "") or profile.get("username", "")
    if display:
        c.setFillColor(C_BLACK)
        set_font(c, 13, bold=True)
        c.drawString(MARGIN, y, display)
        y -= 6*mm

    # Bio
    bio = profile.get("bio", "")
    if bio:
        y -= 3*mm
        # Word wrap bio
        c.setFillColor(C_GRAY_DARK)
        set_font(c, 9)
        lines = []
        words = bio.split()
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 9) < CONTENT_W:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)

        for l in lines[:6]:   # Max 6 lines
            c.drawString(MARGIN, y, l)
            y -= 4.5*mm
        y -= 3*mm

    # Divider
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 6*mm

    # Location
    location = profile.get("location", "")
    if location:
        c.setFillColor(C_GRAY_MID)
        set_font(c, 8)
        c.drawString(MARGIN, y, "📍  " + location)
        y -= 6*mm

    # Stats boxes: Followers | Following
    def stat_box(label, value, bx, by, bw, bh):
        draw_rounded_rect(c, bx, by, bw, bh, r=3*mm, fill_color=C_GRAY_BG)
        num_str = f"{int(value):,}" if value else "—"
        c.setFillColor(C_BLACK)
        set_font(c, 13, bold=True)
        c.drawCentredString(bx + bw/2, by + bh*0.55, num_str)
        c.setFillColor(C_GRAY_MID)
        set_font(c, 8)
        c.drawCentredString(bx + bw/2, by + bh*0.22, label)

    y -= 4*mm
    box_w = (CONTENT_W - 4*mm) / 2
    box_h = 18*mm
    stat_box("Followers", profile.get("followers", 0), MARGIN, y - box_h, box_w, box_h)
    stat_box("Following", profile.get("following", 0), MARGIN + box_w + 4*mm, y - box_h, box_w, box_h)
    y -= box_h + 8*mm

    # Divider
    c.setStrokeColor(C_BORDER)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 6*mm

    # Section label
    c.setFillColor(C_GRAY_MID)
    set_font(c, 8)
    c.drawString(MARGIN, y, "POSTS IN THIS EBOOK")
    y -= 5*mm
    c.setFillColor(C_BLACK)
    set_font(c, 11, bold=True)

    page_number(c, page_num, total_pages)


# ─── POST CARD ────────────────────────────────────────────────────────────
def draw_post_card(c, post, post_index, page_num, total_pages, y_start):
    """
    Draw a single post card starting at y_start.
    Returns the y position after the card (i.e. next available y).
    Returns None if there's not enough space on this page.
    """
    CARD_PADDING = 4 * mm
    MIN_CARD_H = 22 * mm

    # Estimate text height
    text = post.get("text", "") or ""
    has_images = len(post.get("images", [])) > 0
    has_video  = bool(post.get("video_thumbnail"))

    # Text wrapping
    char_per_line = int(CONTENT_W / (9 * 0.55))   # approx chars per line at 9pt
    wrapped = textwrap.wrap(text, width=char_per_line)
    text_lines = wrapped[:12]   # Max 12 lines per card
    truncated = len(wrapped) > 12

    text_h = len(text_lines) * 4.5 * mm if text_lines else 0
    img_h  = 35 * mm if (has_images or has_video) else 0
    meta_h = 8 * mm   # date + likes row
    card_h = CARD_PADDING * 2 + text_h + img_h + meta_h + 4 * mm

    if card_h < MIN_CARD_H:
        card_h = MIN_CARD_H

    # Check if card fits on this page
    card_y = y_start - card_h
    if card_y < MARGIN + 10*mm:
        return None   # Signal: need new page

    # Draw card background
    draw_rounded_rect(c, MARGIN, card_y, CONTENT_W, card_h,
                      r=3*mm, fill_color=C_WHITE, stroke_color=C_BORDER, stroke_width=0.3)

    ty = card_y + card_h - CARD_PADDING

    # Post number badge
    badge_size = 5*mm
    draw_rounded_rect(c, MARGIN + CARD_PADDING, ty - badge_size,
                      badge_size * 2.5, badge_size, r=1.5*mm, fill_color=C_BLACK)
    c.setFillColor(white)
    set_font(c, 7, bold=True)
    c.drawCentredString(MARGIN + CARD_PADDING + badge_size * 1.25, ty - badge_size * 0.6,
                        f"#{post_index + 1}")

    # Date
    date_str = post.get("date_formatted", "") or post.get("timestamp", "")[:10]
    if date_str:
        c.setFillColor(C_GRAY_MID)
        set_font(c, 7.5)
        c.drawRightString(MARGIN + CONTENT_W - CARD_PADDING, ty - badge_size * 0.6, date_str)

    ty -= badge_size + 3*mm

    # Post text
    if text_lines:
        c.setFillColor(C_BLACK)
        set_font(c, 9)
        for line in text_lines:
            c.drawString(MARGIN + CARD_PADDING, ty, line)
            ty -= 4.5*mm
        if truncated:
            c.setFillColor(C_GRAY_MID)
            set_font(c, 8)
            c.drawString(MARGIN + CARD_PADDING, ty, "…")
            ty -= 4*mm

    # Image
    if has_images or has_video:
        img_url = (post.get("images") or [None])[0] or post.get("video_thumbnail")
        if img_url:
            img_data = download_image(img_url)
            if img_data:
                img_buf = image_bytes_to_reportlab(img_data)
                if img_buf:
                    try:
                        img_x = MARGIN + CARD_PADDING
                        img_w = CONTENT_W - 2 * CARD_PADDING
                        ty -= 2*mm
                        c.drawImage(img_buf, img_x, ty - img_h,
                                    width=img_w, height=img_h,
                                    preserveAspectRatio=True, anchor='n')
                        ty -= img_h + 2*mm
                    except Exception as e:
                        logger.warning(f"Failed to draw image in PDF: {e}")

    # Bottom meta row: likes, replies, reposts
    likes   = post.get("likes", 0)
    replies = post.get("replies", 0)
    reposts = post.get("reposts", 0)

    meta_y = card_y + CARD_PADDING + 2*mm
    c.setFillColor(C_GRAY_MID)
    set_font(c, 7.5)

    meta_parts = []
    if likes:   meta_parts.append(f"♡ {likes:,}")
    if replies: meta_parts.append(f"↩ {replies:,} replies")
    if reposts: meta_parts.append(f"↺ {reposts:,}")
    meta_str = "   ".join(meta_parts) if meta_parts else ""
    if meta_str:
        c.drawString(MARGIN + CARD_PADDING, meta_y, meta_str)

    return card_y - 4 * mm   # Gap between cards


# ─── TAIL / STATS PAGE ────────────────────────────────────────────────────
def draw_tail_page(c, profile, posts, page_num, total_pages):
    """Second-to-last page — Stats summary."""
    c.setFillColor(C_WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Header band
    c.setFillColor(C_BLACK)
    c.rect(0, PAGE_H - 22*mm, PAGE_W, 22*mm, fill=1, stroke=0)
    c.setFillColor(white)
    set_font(c, 13, bold=True)
    c.drawCentredString(PAGE_W/2, PAGE_H - 14*mm, "Your Threads in Numbers")
    c.setFillColor(C_GRAY_LIGHT)
    set_font(c, 8)
    c.drawCentredString(PAGE_W/2, PAGE_H - 19*mm, "@" + profile.get("username", ""))

    y = PAGE_H - 34*mm

    # Compute stats
    total_posts   = len(posts)
    total_likes   = sum(p.get("likes", 0) for p in posts)
    total_replies = sum(p.get("replies", 0) for p in posts)
    total_reposts = sum(p.get("reposts", 0) for p in posts)
    posts_w_img   = sum(1 for p in posts if p.get("images"))
    avg_likes     = total_likes // total_posts if total_posts else 0

    def big_stat(label, value, sx, sy, sw, sh):
        draw_rounded_rect(c, sx, sy, sw, sh, r=3*mm, fill_color=C_GRAY_BG)
        c.setFillColor(C_BLACK)
        set_font(c, 15, bold=True)
        val_str = f"{int(value):,}" if isinstance(value, (int, float)) else str(value)
        c.drawCentredString(sx + sw/2, sy + sh*0.58, val_str)
        c.setFillColor(C_GRAY_MID)
        set_font(c, 7.5)
        c.drawCentredString(sx + sw/2, sy + sh*0.22, label)

    bw = (CONTENT_W - 3*mm) / 2
    bh = 16*mm
    gap = 3*mm

    big_stat("Total Posts",    total_posts,   MARGIN,      y - bh, bw, bh)
    big_stat("Total Likes",    total_likes,   MARGIN+bw+gap, y - bh, bw, bh)
    y -= bh + gap

    big_stat("Total Replies",  total_replies, MARGIN,      y - bh, bw, bh)
    big_stat("Total Reposts",  total_reposts, MARGIN+bw+gap, y - bh, bw, bh)
    y -= bh + gap

    big_stat("Posts with Photos", posts_w_img, MARGIN,     y - bh, bw, bh)
    big_stat("Avg Likes/Post", avg_likes,    MARGIN+bw+gap, y - bh, bw, bh)
    y -= bh + gap + 6*mm

    # Footer note
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.3)
    c.line(MARGIN, y, PAGE_W-MARGIN, y)
    y -= 5*mm

    gen_date = datetime.now().strftime("%B %d, %Y")
    c.setFillColor(C_GRAY_MID)
    set_font(c, 7.5)
    c.drawCentredString(PAGE_W/2, y, f"Generated on {gen_date} via Threads Ebook")

    page_number(c, page_num, total_pages)


# ─── BACK COVER ───────────────────────────────────────────────────────────
def draw_back_cover(c, profile):
    """Last page — clean back cover."""
    c.setFillColor(C_BLACK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Subtle border
    c.setStrokeColor(HexColor("#1a1a1a"))
    c.setLineWidth(0.5)
    inset = 6*mm
    c.rect(inset, inset, PAGE_W - 2*inset, PAGE_H - 2*inset, fill=0, stroke=1)

    # @ username centered
    c.setFillColor(HexColor("#333333"))
    set_font(c, 11)
    c.drawCentredString(PAGE_W/2, PAGE_H/2 + 6*mm, "@" + profile.get("username", ""))

    c.setFillColor(HexColor("#222222"))
    set_font(c, 8)
    c.drawCentredString(PAGE_W/2, PAGE_H/2 - 2*mm, "threads.net/@" + profile.get("username", ""))

    # Bottom
    c.setFillColor(HexColor("#1a1a1a"))
    set_font(c, 7)
    c.drawCentredString(PAGE_W/2, inset * 2, "Created with Threads Ebook")


# ─── MAIN GENERATE FUNCTION ───────────────────────────────────────────────
def generate_pdf(profile: dict, posts: list) -> bytes:
    """
    Generate full PDF ebook.
    Returns raw PDF bytes.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    c.setTitle(f"Threads Ebook — @{profile.get('username', 'user')}")
    c.setAuthor(profile.get("username", ""))
    c.setSubject("Threads Ebook")

    # ── Estimate total pages ──────────────────────────────────────────────
    # Rough estimate: 2 posts per page on average
    estimated_post_pages = max(1, len(posts) // 2 + 1)
    total_pages = 2 + estimated_post_pages + 2   # cover + profile + posts + tail + back
    # We'll update post count once done; for now it's a label

    # ── Page 1: Cover ────────────────────────────────────────────────────
    draw_cover(c, profile)
    c.showPage()

    # ── Page 2: Profile ──────────────────────────────────────────────────
    current_page = 2
    draw_profile_page(c, profile, current_page, total_pages)
    c.showPage()

    # ── Pages 3+: Posts ───────────────────────────────────────────────────
    # Each page starts fresh and we pack as many post cards as fit
    post_index = 0
    total_posts = len(posts)

    while post_index < total_posts:
        current_page += 1
        # White background
        c.setFillColor(C_WHITE)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

        # Page header
        c.setFillColor(C_GRAY_BG)
        c.rect(0, PAGE_H - 12*mm, PAGE_W, 12*mm, fill=1, stroke=0)
        c.setFillColor(C_GRAY_MID)
        set_font(c, 7.5)
        c.drawString(MARGIN, PAGE_H - 7.5*mm, "@" + profile.get("username", ""))
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 7.5*mm, "Threads Ebook")

        y = PAGE_H - 14*mm

        # Pack posts onto this page
        while post_index < total_posts:
            post = posts[post_index]
            new_y = draw_post_card(c, post, post_index, current_page, total_pages, y)
            if new_y is None:
                break   # No more room, go to next page
            y = new_y
            post_index += 1

        page_number(c, current_page, total_pages)
        c.showPage()

    # ── Tail page: Stats ──────────────────────────────────────────────────
    current_page += 1
    draw_tail_page(c, profile, posts, current_page, total_pages)
    c.showPage()

    # ── Back cover ────────────────────────────────────────────────────────
    draw_back_cover(c, profile)
    c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
