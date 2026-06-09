"""HTML email rendering — a branded wrapper (header + footer) plus body templates.

Pure rendering, no I/O. Email clients strip <style>/classes and Outlook needs tables,
so everything here is table-based with inline styles. Brand tokens mirror the frontend
`globals.css` (primary #7c4dff, gradient #9747ff→#6f00ff, ink #1e1e22, card #f3f6fb).
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from .config import settings

APP_NAME = "Spiritualized Language Tutor"

# Brand palette (kept in sync with frontend app/globals.css @theme).
_INK = "#1e1e22"
_BODY_TEXT = "#3f3f46"
_MUTED = "#9c9bc2"
_PRIMARY = "#7c4dff"
_PRIMARY_DEEP = "#6f00ff"
_PRIMARY_LIGHT = "#9747ff"
_PAGE_BG = "#e9ebf2"
_CARD_BG = "#ffffff"
_FOOTER_BG = "#f3f6fb"
_FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"


def _site() -> str:
    return settings.FRONTEND_URL.rstrip("/")


def _logo_url() -> str:
    return settings.EMAIL_LOGO_URL or f"{_site()}/little_robot_logo.jpg"


def _button(label: str, url: str) -> str:
    """Gradient CTA rendered as a table cell — Outlook ignores gradients, so bgcolor is the fallback."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:24px 0;"><tr>'
        f'<td align="center" bgcolor="{_PRIMARY_DEEP}" '
        f'style="border-radius:14px;background-image:linear-gradient(120deg,{_PRIMARY_LIGHT},{_PRIMARY_DEEP});">'
        f'<a href="{url}" target="_blank" '
        'style="display:inline-block;padding:14px 30px;font-family:' + _FONT + ";"
        f'font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:14px;">'
        f"{escape(label)}</a></td></tr></table>"
    )


def _footer_link(label: str, href: str) -> str:
    return (
        f'<a href="{href}" target="_blank" '
        f'style="color:{_PRIMARY};text-decoration:none;font-weight:600;">{escape(label)}</a>'
    )


def _layout(*, preheader: str, body_html: str) -> str:
    """Wrap a body fragment in the branded header/footer shell."""
    site = _site()
    year = datetime.now(timezone.utc).year
    footer_links = " &nbsp;·&nbsp; ".join(
        [
            _footer_link("Website", site or "#"),
            _footer_link("Contact", f"{site}/contact"),
            _footer_link("Terms", f"{site}/terms"),
        ]
    )
    return (
        '<!DOCTYPE html>'
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="x-apple-disable-message-reformatting"></head>'
        f'<body style="margin:0;padding:0;background-color:{_PAGE_BG};">'
        # Hidden preheader (inbox preview text).
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{_PAGE_BG};">'
        f"{escape(preheader)}</div>"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background-color:{_PAGE_BG};padding:24px 12px;"><tr><td align="center">'
        f'<table role="presentation" width="480" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:480px;max-width:480px;background-color:{_CARD_BG};border-radius:16px;overflow:hidden;">'
        # Header
        '<tr><td align="center" style="padding:32px 28px 8px 28px;">'
        f'<img src="{_logo_url()}" width="96" alt="{escape(APP_NAME)}" '
        'style="display:block;width:96px;height:auto;border:0;margin:0 auto 12px auto;">'
        f'<div style="font-family:{_FONT};font-size:19px;font-weight:800;color:{_INK};">Spiritualized</div>'
        f'<div style="font-family:{_FONT};font-size:13px;font-weight:700;color:{_PRIMARY};'
        'letter-spacing:.04em;text-transform:uppercase;">Language Tutor</div>'
        '</td></tr>'
        # Body
        f'<tr><td style="padding:8px 28px 28px 28px;font-family:{_FONT};'
        f'font-size:15px;line-height:1.6;color:{_BODY_TEXT};">{body_html}</td></tr>'
        # Footer
        f'<tr><td style="background-color:{_FOOTER_BG};padding:22px 28px;font-family:{_FONT};'
        f'font-size:12px;line-height:1.7;color:{_MUTED};" align="center">'
        f'<div style="margin-bottom:6px;">{footer_links}</div>'
        f'<div>© {year} {escape(APP_NAME)}. All rights reserved.</div>'
        '<div style="margin-top:6px;">You received this email because you have an account with us.</div>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )


def _heading(text: str) -> str:
    return (
        f'<h1 style="margin:0 0 12px 0;font-family:{_FONT};font-size:22px;'
        f'font-weight:800;color:{_INK};">{escape(text)}</h1>'
    )


def _p(html: str) -> str:
    return f'<p style="margin:0 0 14px 0;">{html}</p>'


# --- Body fragments -------------------------------------------------------------

def verification_body(link: str) -> str:
    return (
        _heading("Confirm your email")
        + _p("Welcome to <strong>Spiritualized Language Tutor</strong> 🌌")
        + _p("Confirm your email address to unlock your personal English tutor and start creating learning spaces.")
        + _button("Verify my email", link)
        + _p(
            f'Or paste this link into your browser:<br>'
            f'<a href="{link}" target="_blank" style="color:{_PRIMARY};word-break:break-all;">{escape(link)}</a>'
        )
        + _p(f'<span style="color:{_MUTED};font-size:13px;">This link expires in 24 hours.</span>')
    )


def notification_body(
    *, heading: str, message: str, cta_label: str | None = None, cta_url: str | None = None
) -> str:
    body = _heading(heading) + _p(escape(message))
    if cta_label and cta_url:
        body += _button(cta_label, cta_url)
    return body


def newsletter_body(
    *, heading: str, body_html: str, cta_label: str | None = None, cta_url: str | None = None
) -> str:
    body = _heading(heading) + body_html
    if cta_label and cta_url:
        body += _button(cta_label, cta_url)
    return body


def submission_body(*, heading: str, name: str, email: str, message: str) -> str:
    """Relay an inbound user submission (contact / suggestion) to the team inbox."""
    return (
        _heading(heading)
        + _p(f"<strong>From:</strong> {escape(name)} &lt;{escape(email)}&gt;")
        + _p(escape(message).replace("\n", "<br>"))
    )


# --- Public renderers (body wrapped in the branded layout) ----------------------

def render_verification_email(link: str) -> str:
    return _layout(
        preheader="Confirm your email to start learning with Spiritualized Language Tutor.",
        body_html=verification_body(link),
    )


def render_notification_email(
    *, heading: str, message: str, cta_label: str | None = None, cta_url: str | None = None
) -> str:
    return _layout(
        preheader=message[:120],
        body_html=notification_body(
            heading=heading, message=message, cta_label=cta_label, cta_url=cta_url
        ),
    )


def render_newsletter_email(
    *,
    heading: str,
    body_html: str,
    preheader: str = "",
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> str:
    return _layout(
        preheader=preheader or heading,
        body_html=newsletter_body(
            heading=heading, body_html=body_html, cta_label=cta_label, cta_url=cta_url
        ),
    )


def render_contact_email(*, name: str, email: str, message: str) -> str:
    return _layout(
        preheader=f"New contact message from {name}",
        body_html=submission_body(
            heading="New contact message", name=name, email=email, message=message
        ),
    )


def render_suggestion_email(*, name: str, email: str, message: str) -> str:
    return _layout(
        preheader=f"New suggestion from {name}",
        body_html=submission_body(
            heading="New suggestion 💡", name=name, email=email, message=message
        ),
    )
