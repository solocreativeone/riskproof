"""
Riskproof Telegram Notifier.

Sends structured, human-readable alerts with inline Arbiscan buttons.
"""

import html
import os
import requests
from dotenv import load_dotenv

load_dotenv()


def send_telegram_alert(
    agent_id: str,
    severity: str,
    risk_score: float,
    projected_hf: float,
    reason: str,
    tx_hash: str | None = None,
) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        return False

    severity_upper = severity.upper()
    severity_icon = "🚨" if severity_upper == "CRITICAL" else "⚠️"
    hf_status = "⚠️ Liquidatable" if projected_hf < 1.0 else "Healthy"

    # Clean and escape text for HTML parsing
    safe_agent = html.escape(agent_id)
    safe_reason = html.escape(reason)

    # Clean card layout
    message = (
        f"{severity_icon} <b>RISKPROOF ALERT: {severity_upper}</b>\n"
        f"────────────────────────\n"
        f"<b>Agent:</b> <code>{safe_agent}</code>\n"
        f"<b>Risk Score:</b> <code>{risk_score:.1f} / 100</code>\n"
        f"<b>Projected HF:</b> <code>{projected_hf:.3f}</code> (<i>{hf_status}</i>)\n"
        f"────────────────────────\n"
        f"<b>Context:</b>\n"
        f"<blockquote>{safe_reason}</blockquote>"
    )

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    # Add inline button for the Arbiscan transaction
    if tx_hash:
        clean_tx = tx_hash.removeprefix("0x")
        tx_url = f"https://sepolia.arbiscan.io/tx/0x{clean_tx}"
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "🔗 View Proof on Arbiscan", "url": tx_url}]
            ]
        }

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=5,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[Notifier Network Error]: {e}")
        return False