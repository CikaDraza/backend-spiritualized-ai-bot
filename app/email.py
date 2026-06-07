from __future__ import annotations

import logging

from fastapi.concurrency import run_in_threadpool

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
    return f"{settings.BACKEND_URL.rstrip('/')}/auth/verify?token={raw_token}"


def _verification_html(link: str) -> str:
    return (
        "<p>Welcome to <strong>Spiritualized</strong> 🌌</p>"
        "<p>Confirm your email to unlock your personal English tutor:</p>"
        f'<p><a href="{link}">Verify my email</a></p>'
        f'<p>Or paste this link: {link}</p>'
    )


async def send_verification_email(to_email: str, raw_token: str) -> None:
    """Send the verification email via Resend, or log the link if email isn't configured."""
    link = build_verification_link(raw_token)

    if not is_email_configured():
        logger.warning(
            "EMAIL DEV-FALLBACK (Resend not configured) — verification link for %s: %s",
            to_email,
            link,
        )
        return

    def _send() -> None:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send(
            {
                "from": settings.EMAIL_FROM,
                "to": [to_email],
                "subject": "Verify your Spiritualized account",
                "html": _verification_html(link),
            }
        )

    try:
        await run_in_threadpool(_send)
        logger.info("Verification email sent to %s", to_email)
    except Exception as exc:  # never let email failure break registration
        logger.error("Failed to send verification email to %s: %s", to_email, exc)
        logger.warning("Verification link for %s: %s", to_email, link)
