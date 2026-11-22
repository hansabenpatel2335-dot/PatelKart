"""
telegram_notify.py
==================
Sends Telegram notifications to the shop owner whenever a new user
registers or an order is placed on PatelKart.

Setup
-----
1. Create a bot with @BotFather on Telegram → copy the token.
2. Start a conversation with your bot (or add it to a group).
3. Get your chat ID:  https://api.telegram.org/bot<TOKEN>/getUpdates
4. Add to Streamlit secrets (.streamlit/secrets.toml):

    [telegram]
    bot_token = "123456:ABC-DEF..."
    chat_id   = "987654321"

Or set environment variables: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
"""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)


def _get_credentials() -> tuple[str | None, str | None]:
    """Return (bot_token, chat_id) from Streamlit secrets or env vars."""
    bot_token: str | None = None
    chat_id: str | None = None

    # Try Streamlit secrets first (works in Streamlit Cloud)
    try:
        import streamlit as st  # noqa: PLC0415

        tg = st.secrets.get("telegram", {})
        bot_token = tg.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = tg.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    except Exception:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

    return bot_token, chat_id


def _send(text: str) -> bool:
    """
    POST a plain-text message to the Telegram Bot API.
    Returns True on success, False on failure (never raises).
    """
    bot_token, chat_id = _get_credentials()

    if not bot_token or not chat_id:
        logger.warning(
            "Telegram credentials not configured — "
            "set [telegram] bot_token / chat_id in .streamlit/secrets.toml "
            "or via TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env vars."
        )
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps(
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    ).encode()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.load(response)
            if not result.get("ok"):
                logger.error("Telegram API error: %s", result)
                return False
        return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        logger.error("Telegram HTTP %s: %s", exc.code, body)
    except Exception as exc:  # noqa: BLE001
        logger.error("Telegram send failed: %s", exc)
    return False


# ──────────────────────────────────────────────────────────────
# Public helpers (called from app.py)
# ──────────────────────────────────────────────────────────────

def notify_new_user(username: str, full_name: str, phone: str) -> None:
    """
    Send a Telegram alert when a new account is created.

    Args:
        username:  The chosen username.
        full_name: The user's full name.
        phone:     The user's phone number.
    """
    name_display = full_name.strip() or username
    phone_display = phone.strip() or "—"

    message = (
        "🛍️ <b>PatelKart — New Account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> {name_display}\n"
        f"🔑 <b>Username:</b> {username}\n"
        f"📱 <b>Phone:</b> {phone_display}"
    )
    _send(message)


def notify_new_order(
    username: str,
    order_id: int,
    items: list[dict],
    total: float,
) -> None:
    """
    Send a Telegram alert when an order is placed.

    Args:
        username: The customer's username.
        order_id: The newly created order ID.
        items:    List of dicts with keys: product_name, unit_price, quantity.
        total:    The order grand total (₹).
    """
    lines = [
        f"🛒 <b>PatelKart — New Order #{order_id}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 <b>Customer:</b> {username}",
        "",
        "<b>Items:</b>",
    ]
    for item in items:
        subtotal = item["unit_price"] * item["quantity"]
        lines.append(
            f"  • {item['quantity']}× {item['product_name']}  "
            f"→ ₹{subtotal:,.2f}".rstrip("0").rstrip(".")
        )

    lines += [
        "",
        f"💰 <b>Total:</b> ₹{total:,.2f}".rstrip("0").rstrip("."),
    ]

    _send("\n".join(lines))


def notify_login(username: str) -> None:
    """
    Send a Telegram alert when a user logs in.

    Args:
        username: The username of the person who just logged in.
    """
    message = (
        "🔐 <b>PatelKart — User Logged In</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Username:</b> {username}"
    )
    _send(message)
