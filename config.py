from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "SelectionTranslator" / "config.json"
DEFAULT_SETTINGS = {
    "appid": "",
    "secret_key": "",
    "target_lang": "zh",
}


def load_settings() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    return {**DEFAULT_SETTINGS, **saved}


def save_settings(appid: str, secret_key: str, target_lang: str) -> None:
    settings = {
        "appid": appid.strip(),
        "secret_key": secret_key.strip(),
        "target_lang": target_lang,
    }
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = CONFIG_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(CONFIG_PATH)
