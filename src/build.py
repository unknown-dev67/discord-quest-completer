import re
import logging

import requests

import src.headers as hdr
from src.constants import USER_AGENT

log = logging.getLogger(__name__)


def update_build_number():
    try:
        log.info("Fetching latest Discord build number...")
        resp = requests.get("https://discord.com/app", headers={"User-Agent": USER_AGENT}, timeout=15)
        if resp.status_code != 200:
            log.warning("Failed to fetch Discord page (status %s)", resp.status_code)
            return
        scripts = re.findall(r'/assets/web\.([a-f0-9]+)\.js', resp.text)
        if not scripts:
            log.warning("No JS assets found.")
            return
        for script_hash in scripts:
            js_url = f"https://discord.com/assets/web.{script_hash}.js"
            try:
                js_resp = requests.get(js_url, headers={"User-Agent": USER_AGENT}, timeout=15)
                if js_resp.status_code != 200:
                    continue
                match = re.search(r'buildNumber["\s:]+["\s]*(\d{5,7})', js_resp.text)
                if match:
                    build_num = int(match.group(1))
                    log.info("Discord build number: %s", build_num)
                    hdr.set_build_number(build_num)
                    return
            except Exception:
                continue
        log.warning("Build number not found in JS assets.")
    except Exception as e:
        log.error("Error fetching build number: %s", e)
