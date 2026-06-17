import logging

import src.rest as rest

log = logging.getLogger(__name__)


# ---------- Quest dict accessors ----------

def quest_id(quest):
    return quest["id"]


def quest_config(quest):
    return quest["config"]


def quest_user_status(quest):
    return quest.get("user_status") or {}


def quest_is_completed(quest):
    return bool(quest_user_status(quest).get("completed_at"))


def quest_is_enrolled(quest):
    return bool(quest_user_status(quest).get("enrolled_at"))


def quest_is_expired(quest):
    import time
    from datetime import datetime
    exp = quest_config(quest)["expires_at"]
    exp_ts = datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
    return time.time() > exp_ts


def quest_update_status(quest, new_status):
    quest["user_status"] = new_status


# ---------- Fetch ----------

def fetch_quests(token):
    resp = rest.get(token, "/quests/@me")
    blocked = resp.get("quest_enrollment_blocked_until")
    if blocked is not None:
        raise Exception(f"Quest enrollment blocked until {blocked}")
    quests = resp.get("quests", [])
    log.info("Fetched %d quest(s).", len(quests))
    return quests


def filter_todo(quests):
    return [q for q in quests if not quest_is_completed(q) and not quest_is_expired(q)]


# ---------- Enroll ----------

def accept_quest(token, quest, is_android=False):
    qname = quest_config(quest)["messages"]["quest_name"]
    body = {
        "location": 12 if is_android else 11,
        "is_targeted": False,
        "metadata_sealed": None,
        "traffic_metadata_raw": quest.get("traffic_metadata_raw"),
        "traffic_metadata_sealed": quest.get("traffic_metadata_sealed"),
    }
    extra = {"AndroidRequest": "true" if is_android else "false"}
    resp = rest.post(token, f"/quests/{quest_id(quest)}/enroll", body=body, extra_headers=extra)
    quest_update_status(quest, resp)
    log.info("Enrolled in quest '%s'.", qname)
