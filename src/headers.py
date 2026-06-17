import json
import base64

from src.constants import USER_AGENT, ANDROID_USER_AGENT, desktop_properties, android_properties

# module-level build number, updated by build.py
_build_number = 539951


def set_build_number(n):
    global _build_number
    _build_number = n


def make_desktop_headers(with_properties=True, with_origin=True):
    headers = {
        "accept-language": "en-US",
        "User-Agent": USER_AGENT,
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    if with_origin:
        headers["origin"] = "https://discord.com"
        headers["referer"] = "https://discord.com/channels/@me"
    if with_properties:
        props = desktop_properties(build_number=_build_number)
        headers["x-super-properties"] = base64.b64encode(json.dumps(props).encode()).decode()
    return headers


def make_android_headers(with_properties=True):
    headers = {
        "accept-language": "en-US",
        "User-Agent": ANDROID_USER_AGENT,
    }
    if with_properties:
        props = android_properties()
        headers["x-super-properties"] = base64.b64encode(json.dumps(props).encode()).decode()
    return headers


def make_headers(init_headers=None):
    headers = dict(init_headers) if init_headers else {}
    is_android = headers.pop("AndroidRequest", "false") == "true"
    auth = headers.get("Authorization", "")
    if auth.startswith("Bot "):
        headers["Authorization"] = auth[4:]
    headers["accept-language"] = "en-US"
    headers["x-debug-options"] = "bugReporterEnabled"
    headers["x-discord-locale"] = "en-US"
    headers["x-discord-timezone"] = "Asia/Saigon"
    extra = make_android_headers() if is_android else make_desktop_headers()
    headers.update(extra)
    return headers


def get_activity_headers(quest_id, auth_token="", activity_referrer=""):
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": auth_token,
        "X-Discord-Quest-ID": quest_id,
    }
    if activity_referrer:
        headers["Referer"] = activity_referrer
    return headers
