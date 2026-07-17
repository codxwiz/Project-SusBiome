"""Public contact-form endpoint backed by authenticated SMTP."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["Contact"])

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^[0-9+()\-\s.]+$")


class ContactRequest(BaseModel):
    """Validated public contact-form payload."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    address: str | None = Field(default=None, max_length=300)
    message: str | None = Field(default=None, max_length=4000)
    website: str | None = Field(default=None, max_length=200)

    @field_validator("email", "address", "message", "website", mode="before")
    @classmethod
    def empty_strings_are_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("name", "phone", "email")
    @classmethod
    def reject_header_newlines(cls, value: str | None) -> str | None:
        if value is not None and ("\r" in value or "\n" in value):
            raise ValueError("Line breaks are not allowed in this field.")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid phone number.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value


@dataclass(frozen=True, slots=True)
class SMTPConfiguration:
    host: str
    port: int
    username: str
    password: str
    sender: str
    recipient: str
    use_ssl: bool


def _smtp_configuration() -> SMTPConfiguration | None:
    username = os.getenv("SUSBIOME_SMTP_USERNAME", "").strip()
    password = os.getenv("SUSBIOME_SMTP_PASSWORD", "").strip()
    if not username or not password:
        return None

    try:
        port = int(os.getenv("SUSBIOME_SMTP_PORT", "587"))
    except ValueError as error:
        raise RuntimeError("SUSBIOME_SMTP_PORT must be an integer.") from error

    return SMTPConfiguration(
        host=os.getenv("SUSBIOME_SMTP_HOST", "").strip() or "smtp.gmail.com",
        port=port,
        username=username,
        password=password,
        sender=os.getenv("SUSBIOME_CONTACT_FROM", "").strip() or username,
        recipient=(
            os.getenv("SUSBIOME_CONTACT_TO", "").strip() or "susbiome098@gmail.com"
        ),
        use_ssl=os.getenv("SUSBIOME_SMTP_USE_SSL", "false").lower() == "true",
    )


def _email_message(payload: ContactRequest, config: SMTPConfiguration) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "New SusBiome website enquiry"
    message["From"] = config.sender
    message["To"] = config.recipient
    if payload.email:
        message["Reply-To"] = payload.email

    message.set_content(
        "\n".join(
            [
                "A new enquiry was submitted through susbiome.com.",
                "",
                f"Name: {payload.name}",
                f"Phone: {payload.phone}",
                f"Email: {payload.email or 'Not provided'}",
                f"Address: {payload.address or 'Not provided'}",
                "",
                "Message:",
                payload.message or "Not provided",
            ]
        )
    )
    return message


def _send_email(payload: ContactRequest, config: SMTPConfiguration) -> None:
    message = _email_message(payload, config)
    context = ssl.create_default_context()

    if config.use_ssl:
        with smtplib.SMTP_SSL(config.host, config.port, timeout=15, context=context) as client:
            client.login(config.username, config.password)
            client.send_message(message)
        return

    with smtplib.SMTP(config.host, config.port, timeout=15) as client:
        client.ehlo()
        client.starttls(context=context)
        client.ehlo()
        client.login(config.username, config.password)
        client.send_message(message)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_contact(payload: ContactRequest, request: Request) -> dict[str, bool]:
    """Email one validated website enquiry to the configured SusBiome inbox."""
    if payload.website:
        return {"accepted": True}

    try:
        config = _smtp_configuration()
    except RuntimeError as error:
        logger.error("Contact SMTP configuration is invalid: %s", error)
        raise HTTPException(status_code=503, detail="Contact service is unavailable.") from error

    if config is None:
        raise HTTPException(status_code=503, detail="Contact service is unavailable.")

    try:
        await asyncio.to_thread(_send_email, payload, config)
    except (OSError, smtplib.SMTPException, ValueError):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("Contact email delivery failed request_id=%s", request_id)
        raise HTTPException(status_code=502, detail="Unable to send the enquiry right now.")

    return {"accepted": True}
