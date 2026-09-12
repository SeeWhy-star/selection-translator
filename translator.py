from __future__ import annotations

import hashlib
import secrets

import requests

API_ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"
MAX_QUERY_BYTES = 6000


class TranslationError(RuntimeError):
    pass


def translate(text: str, appid: str, secret_key: str, target_lang: str) -> str:
    if not text.strip():
        raise TranslationError("没有获取到选中的文本。")
    if len(text.encode("utf-8")) > MAX_QUERY_BYTES:
        raise TranslationError("单次翻译不能超过 6000 个字节，请缩短选中文本。")

    salt = secrets.token_hex(12)
    signature = hashlib.md5(
        f"{appid}{text}{salt}{secret_key}".encode("utf-8")
    ).hexdigest()
    response = requests.get(
        API_ENDPOINT,
        params={
            "q": text,
            "from": "auto",
            "to": target_lang,
            "appid": appid,
            "salt": salt,
            "sign": signature,
        },
        timeout=12,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as error:
        raise TranslationError("百度翻译返回了无法识别的响应。") from error

    if "error_code" in payload:
        error_code = payload["error_code"]
        if error_code == "52003":
            raise TranslationError(
                "百度 API 授权失败（52003）。请按 Alt+Shift+Q，填写百度后台的纯数字 APP ID 和对应密钥。"
            )
        message = payload.get("error_msg", "未知错误")
        raise TranslationError(f"百度翻译错误 {error_code}：{message}")

    results = payload.get("trans_result")
    if not results:
        raise TranslationError("百度翻译没有返回译文。")

    return "\n".join(item["dst"] for item in results)
