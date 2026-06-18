import time
import random
import logging
import urllib.parse
from datetime import datetime

import requests

import rest
from src.headers import make_desktop_headers, get_activity_headers
from src.quests import quest_id, quest_config, quest_user_status, quest_is_completed, quest_update_status

log = logging.getLogger(__name__)

TASK_TYPES = [
    "WATCH_VIDEO",
    "WATCH_VIDEO_ON_MOBILE",
    "PLAY_ON_DESKTOP",
    "PLAY_ON_XBOX",
    "PLAY_ON_PLAYSTATION",
    "STREAM_ON_DESKTOP",
    "PLAY_ACTIVITY",
    "ACHIEVEMENT_IN_ACTIVITY",
]


def do_watch_video(token, quest, seconds_needed, seconds_done):
    qname = quest_config(quest)["messages"]["quest_name"]
    max_future = 10
    speed = 7
    interval = 7
    enrolled_at = datetime.fromisoformat(
        quest_user_status(quest)["enrolled_at"].replace("Z", "+00:00")
    ).timestamp()
    completed = False
    log.info("Spoofing video watch for '%s'...", qname)
    while True:
        max_allowed = int((time.time() - enrolled_at) + max_future)
        diff = max_allowed - seconds_done
        timestamp = seconds_done + speed
        if diff >= speed:
            new_ts = min(seconds_needed, timestamp + random.random())
            resp = rest.post(token, f"/quests/{quest_id(quest)}/video-progress", body={"timestamp": new_ts})
            completed = resp.get("completed_at") is not None
            seconds_done = min(seconds_needed, timestamp)
        if seconds_done >= seconds_needed:
            break
        time.sleep(interval)
    if not completed:
        rest.post(token, f"/quests/{quest_id(quest)}/video-progress", body={"timestamp": seconds_needed})
    log.info("Quest '%s' completed!", qname)


def do_play_on_platform(token, quest, seconds_needed, task_name):
    qname = quest_config(quest)["messages"]["quest_name"]
    application_id = quest_config(quest)["application"]["id"]
    interval = 20
    log.info("Spoofing platform play for '%s'...", qname)
    while not quest_is_completed(quest):
        seconds_done = quest_user_status(quest).get("progress", {}).get(task_name, {}).get("value", 0)
        remaining = max(0, seconds_needed - seconds_done)
        log.info("Progress: %ds done, ~%d min remaining.", seconds_done, int(remaining / 60))
        try:
            resp = rest.post(
                token,
                f"/quests/{quest_id(quest)}/heartbeat",
                body={"application_id": application_id, "terminal": False},
            )
            quest_update_status(quest, resp)
        except Exception as e:
            if "500" in str(e):
                log.warning("Discord having issues (500), retrying in 10s...")
                time.sleep(10)
                continue
            raise
        time.sleep(interval)
    rest.post(
        token,
        f"/quests/{quest_id(quest)}/heartbeat",
        body={"application_id": application_id, "terminal": True},
    )
    log.info("Quest '%s' completed!", qname)


def do_play_activity(token, quest, seconds_needed, task_name):
    qname = quest_config(quest)["messages"]["quest_name"]
    stream_key = "call:1:1"
    interval = 20
    log.info("Spoofing activity play for '%s'...", qname)
    while not quest_is_completed(quest):
        seconds_done = quest_user_status(quest).get("progress", {}).get(task_name, {}).get("value", 0)
        remaining = max(0, seconds_needed - seconds_done)
        log.info("Progress: %ds done, ~%d min remaining.", seconds_done, int(remaining / 60))
        try:
            resp = rest.post(
                token,
                f"/quests/{quest_id(quest)}/heartbeat",
                body={"stream_key": stream_key, "terminal": False},
            )
            quest_update_status(quest, resp)
        except Exception as e:
            if "500" in str(e):
                log.warning("Discord 500 error, retrying in 10s...")
                time.sleep(10)
                continue
            raise
        time.sleep(interval)
    rest.post(token, f"/quests/{quest_id(quest)}/heartbeat", body={"stream_key": stream_key, "terminal": True})
    log.info("Quest '%s' completed!", qname)


def _get_proxy_ticket(token, application_id):
    resp = rest.post(token, f"/applications/{application_id}/proxy-tickets", body={})
    return resp["ticket"]


def _get_activity_referrer(token, application_id):
    ticket = _get_proxy_ticket(token, application_id)
    params = urllib.parse.urlencode({
        "instance_id": "example-cl-instance",
        "platform": "desktop",
        "discord_proxy_ticket": ticket,
    })
    return f"https://{application_id}.discordsays.com/?{params}"


def _authorize_discord_says(token, application_id, quest_id_val, auth_code):
    activity_referrer = _get_activity_referrer(token, application_id)
    headers = make_desktop_headers(False, False)
    headers.update(get_activity_headers(quest_id_val, "", activity_referrer))
    url = f"https://{application_id}.discordsays.com/.proxy/acf/authorize"
    try:
        resp = requests.post(url, json={"code": auth_code}, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("token"), None, activity_referrer
    except Exception as e:
        return None, str(e), activity_referrer


def _progress_discord_says(application_id, quest_id_val, auth_token, quest_target, activity_referrer):
    headers = make_desktop_headers(False, False)
    headers.update(get_activity_headers(quest_id_val, auth_token, activity_referrer))
    url = f"https://{application_id}.discordsays.com/.proxy/acf/quest/progress"
    try:
        resp = requests.post(url, json={"progress": quest_target}, headers=headers, timeout=30)
        resp.raise_for_status()
        return True, None
    except Exception as e:
        return False, str(e)


def do_achievement_in_activity(token, quest):
    qname = quest_config(quest)["messages"]["quest_name"]
    application_id = quest_config(quest)["application"]["id"]
    application_name = quest_config(quest)["application"]["name"]
    quest_target = quest_config(quest)["task_config_v2"]["tasks"]["ACHIEVEMENT_IN_ACTIVITY"]["target"]

    # 1. OAuth2 authorize
    query = "&".join([
        "response_type=code",
        f"client_id={application_id}",
        "scope=identify applications.commands applications.entitlements",
        "state=",
    ])
    resp = rest.post(token, f"/oauth2/authorize?{query}", body={
        "permissions": "0",
        "authorize": True,
        "integration_type": 1,
        "location_context": {"guild_id": "10000", "channel_id": "10000", "channel_type": 10000},
    })
    location = resp.get("location")
    auth_code = None
    if location:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
        auth_code = qs.get("code", [None])[0]
    if not auth_code:
        log.error("No auth code received for '%s'. Cannot complete.", application_name)
        return

    # 2. Discord Says auth
    ds_token, error, activity_referrer = _authorize_discord_says(token, application_id, quest_id(quest), auth_code)
    if error or not ds_token:
        log.error("Failed to authorize Discord Says for '%s': %s", qname, error)
        return

    # 3. Progress
    success, err = _progress_discord_says(application_id, quest_id(quest), ds_token, quest_target, activity_referrer)
    if not success:
        log.error("Failed to progress quest '%s': %s", qname, err)
        return

    # 4. Deauthorize
    tokens = rest.get(token, "/oauth2/tokens")
    for t in tokens:
        if t.get("application", {}).get("id") == application_id:
            try:
                rest.delete(token, f"/oauth2/tokens/{t['id']}")
                log.info("Deauthorized application '%s'.", application_name)
            except Exception as e:
                log.error("Failed to deauthorize '%s': %s", application_name, e)
            break

    log.info("Quest '%s' completed!", qname)


def run_task(token, quest):
    qname = quest_config(quest)["messages"]["quest_name"]
    task_config = quest_config(quest)["task_config_v2"]
    task_name = next((t for t in TASK_TYPES if t in task_config["tasks"]), None)
    if not task_name:
        log.warning("No known task type found for '%s'. Skipping.", qname)
        return

    seconds_needed = task_config["tasks"][task_name]["target"]
    seconds_done = quest_user_status(quest).get("progress", {}).get(task_name, {}).get("value", 0)

    if task_name in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"):
        do_watch_video(token, quest, seconds_needed, seconds_done)
    elif task_name in ("PLAY_ON_XBOX", "PLAY_ON_PLAYSTATION", "PLAY_ON_DESKTOP"):
        do_play_on_platform(token, quest, seconds_needed, task_name)
    elif task_name == "PLAY_ACTIVITY":
        do_play_activity(token, quest, seconds_needed, task_name)
    elif task_name == "STREAM_ON_DESKTOP":
        log.warning("STREAM_ON_DESKTOP is unsupported. Complete '%s' manually in the Discord app.", qname)
    elif task_name == "ACHIEVEMENT_IN_ACTIVITY":
        do_achievement_in_activity(token, quest)
    else:
        log.warning("Unhandled task type '%s' for quest '%s'. Skipping.", task_name, qname)
