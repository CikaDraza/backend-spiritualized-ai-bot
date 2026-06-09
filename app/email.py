from __future__ import annotations

import logging

from fastapi.concurrency import run_in_threadpool

from . import email_templates
from .config import settings

logger = logging.getLogger("spiritualized.email")

# Treat these as "not configured" so we fall back to logging the link.
_PLACEHOLDER_KEYS = {"", "re_xxx", "your-resend-api-key"}


def is_email_configured() -> bool:
    """True only when a real Resend key and a non-placeholder sender are present."""
    return (
        settings.RESEND_API_KEY not in _PLACEHOLDER_KEYS
        and "yourdomain.com" not in settings.EMAIL_FROM
    )


def build_verification_link(raw_token: str) -> str:
    """Point at the frontend /verify page (which toasts + redirects), not the raw backend JSON."""
    return f"{settings.FRONTEND_URL.rstrip('/')}/verify?token={raw_token}"


async def send_email(
    *, to: str, subject: str, html: str, from_addr: str | None = None
) -> bool:
    """Send one HTML email via Resend. Returns True if actually sent.

    Falls back to logging (and returning False) when email isn't configured or the send fails,
    so a delivery problem never breaks the calling request (e.g. registration).
    """
    if not is_email_configured():
        logger.warning("EMAIL DEV-FALLBACK (Resend not configured) — would send %r to %s", subject, to)
        return False

    sender = from_addr or settings.EMAIL_FROM

    def _send() -> None:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {"from": sender, "to": [to], "subject": subject, "html": html}
        )

    try:
        await run_in_threadpool(_send)
        logger.info("Email %r sent to %s", subject, to)
        return True
    except Exception as exc:  # never let email failure break the caller
        logger.error("Failed to send email %r to %s: %s", subject, to, exc)
        return False


async def send_verification_email(to_email: str, raw_token: str) -> None:
    """Send the branded verification email, or log the link if email isn't configured."""
    link = build_verification_link(raw_token)
    sent = await send_email(
        to=to_email,
        subject="Verify your Spiritualized account",
        html=email_templates.render_verification_email(link),
    )
    if not sent:
        logger.warning("Verification link for %s: %s", to_email, link)


# --- Convenience senders for the other branded templates ------------------------
# Ready to use; no app flow triggers these yet (no notification/newsletter/contact feature).

async def send_notification_email(
    *,
    to_email: str,
    subject: str,
    heading: str,
    message: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> bool:
    return await send_email(
        to=to_email,
        subject=subject,
        html=email_templates.render_notification_email(
            heading=heading, message=message, cta_label=cta_label, cta_url=cta_url
        ),
    )


async def send_newsletter_email(
    *,
    to_email: str,
    subject: str,
    heading: str,
    body_html: str,
    preheader: str = "",
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> bool:
    return await send_email(
        to=to_email,
        subject=subject,
        html=email_templates.render_newsletter_email(
            heading=heading,
            body_html=body_html,
            preheader=preheader,
            cta_label=cta_label,
            cta_url=cta_url,
        ),
    )


async def send_contact_email(
    *, to_email: str, name: str, email: str, message: str
) -> bool:
    return await send_email(
        to=to_email,
        subject=f"New contact message from {name}",
        html=email_templates.render_contact_email(name=name, email=email, message=message),
    )
