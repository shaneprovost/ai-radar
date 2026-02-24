"""Slack incoming webhook delivery."""
from __future__ import annotations
import json

import httpx


def post_to_slack(
    webhook_url: str,
    digest_path: str,
    item_count: int,
    date_str: str,
) -> bool:
    """Post a digest summary to Slack. Returns True on success."""
    message = {
        "text": (
            f"*AI Radar Digest — {date_str}* ({item_count} items)\n"
            f"Your weekly personalized AI digest is ready.\n"
            f"📄 `{digest_path}`\n"
            f"Run `ai-radar digest` to refresh."
        ),
        "mrkdwn": True,
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                webhook_url,
                content=json.dumps(message),
                headers={"Content-Type": "application/json"},
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"[Slack] delivery error: {e}")
        return False
