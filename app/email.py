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
        and "yourdomain.com" not in settings.EMAIL_FROM_DEFAULT
    )


def build_verification_link(raw_token: str) -> str:
    """Point at the frontend /verify page (which toasts + redirects), not the raw backend JSON."""
    return f"{settings.FRONTEND_URL.rstrip('/')}/verify?token={raw_token}"


def _addr_of(value: str) -> str:
    """Extract the bare address from a `Name <addr@domain>` (or a plain address)."""
    if "<" in value and ">" in value:
        return value[value.index("<") + 1 : value.index(">")].strip()
    return value.strip()


def _email_domain() -> str:
    """The verified Resend domain — EMAIL_DOMAIN, else parsed out of EMAIL_FROM_DEFAULT."""
    if settings.EMAIL_DOMAIN:
        return settings.EMAIL_DOMAIN.strip()
    addr = _addr_of(settings.EMAIL_FROM_DEFAULT)
    return addr.rsplit("@", 1)[-1] if "@" in addr else ""


def _from(override: str, local: str, name: str = "Spiritualized Tutor") -> str:
    """A category sender: the explicit override, else `Name <local@domain>`, else the default."""
    if override:
        return override
    domain = _email_domain()
    return f"{name} <{local}@{domain}>" if domain else settings.EMAIL_FROM_DEFAULT


def _contact_address() -> str:
    """Bare contact@ address — where replies to system/marketing mail are routed."""
    return _addr_of(_from(settings.EMAIL_FROM_CONTACT, "contact"))


async def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    from_addr: str | None = None,
    reply_to: str | None = None,
) -> bool:
    """Send one HTML email via Resend. Returns True if actually sent.

    Falls back to logging (and returning False) when email isn't configured or the send fails,
    so a delivery problem never breaks the calling request (e.g. registration).
    """
    if not is_email_configured():
        logger.warning("EMAIL DEV-FALLBACK (Resend not configured) — would send %r to %s", subject, to)
        return False

    from_value = from_addr or settings.EMAIL_FROM_DEFAULT

    def _send() -> None:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        params: dict[str, object] = {
            "from": from_value,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to
        resend.Emails.send(params)  # type: ignore[arg-type]

    try:
        await run_in_threadpool(_send)
        logger.info("Email %r sent from %s to %s", subject, from_value, to)
        return True
    except Exception as exc:  # never let email failure break the caller
        logger.error("Failed to send email %r to %s: %s", subject, to, exc)
        return False


async def send_verification_email(to_email: str, raw_token: str) -> None:
    """Send the branded verification email, or log the link if email isn't configured."""
    # System mail → noreply (EMAIL_FROM_DEFAULT); replies routed to the monitored contact inbox.
    link = build_verification_link(raw_token)
    sent = await send_email(
        to=to_email,
        subject="Verify your Spiritualized account",
        reply_to=_contact_address(),
        html=email_templates.render_verification_email(link),
    )
    if not sent:
        logger.warning("Verification link for %s: %s", to_email, link)


# --- Per-category senders ---------------------------------------------------------
# Each goes from its own alias on the verified domain. Senders to the user (system / newsletter /
# info) route replies to contact@; inbound relays (contact / suggestions) reply to the submitter.
# Ready to use; only verification is wired to a flow so far.

async def send_notification_email(
    *,
    to_email: str,
    subject: str,
    heading: str,
    message: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> bool:
    # System nudge (e.g. "continue your lesson") → noreply, replies to contact@.
    return await send_email(
        to=to_email,
        subject=subject,
        reply_to=_contact_address(),
        html=email_templates.render_notification_email(
            heading=heading, message=message, cta_label=cta_label, cta_url=cta_url
        ),
    )


async def send_info_email(
    *,
    to_email: str,
    subject: str,
    heading: str,
    message: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> bool:
    # General info / welcome / updates → info@, replies to contact@.
    return await send_email(
        to=to_email,
        subject=subject,
        from_addr=_from(settings.EMAIL_FROM_INFO, "info"),
        reply_to=_contact_address(),
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
    # Campaign → newsletter@, replies to contact@.
    return await send_email(
        to=to_email,
        subject=subject,
        from_addr=_from(settings.EMAIL_FROM_NEWSLETTER, "newsletter"),
        reply_to=_contact_address(),
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
    # Inbound contact-form relay to your inbox: from contact@, reply goes to the submitter.
    return await send_email(
        to=to_email,
        subject=f"New contact message from {name}",
        from_addr=_from(settings.EMAIL_FROM_CONTACT, "contact"),
        reply_to=email,
        html=email_templates.render_contact_email(name=name, email=email, message=message),
    )


async def send_suggestion_email(
    *, to_email: str, name: str, email: str, message: str
) -> bool:
    # Inbound suggestion relay: from suggestions@, reply goes to the submitter.
    return await send_email(
        to=to_email,
        subject=f"New suggestion from {name}",
        from_addr=_from(settings.EMAIL_FROM_SUGGESTIONS, "suggestions"),
        reply_to=email,
        html=email_templates.render_suggestion_email(name=name, email=email, message=message),
    )
