import time
import logging

import requests

from src.constants import DISCORD_API, USER_AGENT
from src.headers import make_headers

log = logging.getLogger(__name__)

_session = None


def get_session(token):
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"Authorization": token, "User-Agent": USER_AGENT})
    return _session


def request(token, method, path, body=None, extra_headers=None, query=None):
    session = get_session(token)
    url = DISCORD_API + path
    headers = make_headers(extra_headers or {})
    headers["Authorization"] = token
    if query:
        url += "?" + "&".join(f"{k}={v}" for k, v in query.items())
    resp = session.request(method, url, json=body, headers=headers, timeout=60)
    if resp.status_code == 429:
        retry_after = float(resp.headers.get("Retry-After", 1))
        log.warning("Rate limited. Retrying in %.1fs", retry_after)
        time.sleep(retry_after)
        return request(token, method, path, body, extra_headers, query)
    resp.raise_for_status()
    return None if resp.status_code == 204 else resp.json()


def get(token, path, query=None, extra_headers=None):
    return request(token, "GET", path, query=query, extra_headers=extra_headers)


def post(token, path, body=None, extra_headers=None):
    return request(token, "POST", path, body=body, extra_headers=extra_headers)


def delete(token, path, extra_headers=None):
    return request(token, "DELETE", path, extra_headers=extra_headers)
