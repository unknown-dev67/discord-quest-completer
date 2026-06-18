import os
import sys
import logging
import threading
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import build
import rest
import quests
import tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

REWARD_TYPE_ORBS       = 4
REWARD_TYPE_DECORATION = 3

TASK_ORDER = [
    "WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE", "PLAY_ON_DESKTOP",
    "PLAY_ON_XBOX", "PLAY_ON_PLAYSTATION", "PLAY_ACTIVITY",
    "ACHIEVEMENT_IN_ACTIVITY", "STREAM_ON_DESKTOP",
]


def get_reward_name(quest):
    rewards = quests.quest_config(quest).get("rewards_config", {}).get("rewards", [])
    if rewards:
        return rewards[0].get("messages", {}).get("name", "Unknown")
    return "Unknown"


def get_reward_types(quest):
    rewards = quests.quest_config(quest).get("rewards_config", {}).get("rewards", [])
    return {r.get("type") for r in rewards}


def get_task_type(quest):
    task_cfg = quests.quest_config(quest).get("task_config_v2", {}).get("tasks", {})
    return next((t for t in TASK_ORDER if t in task_cfg), "UNKNOWN")


def get_time_remaining(quest):
    exp = quests.quest_config(quest)["expires_at"]
    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
    diff = exp_dt - datetime.now(timezone.utc)
    days = max(0, diff.days)
    hours = diff.seconds // 3600
    return f"{days}d {hours}h"


def print_quest_list(quest_list):
    print()
    print("Available quests:")
    print()
    for i, q in enumerate(quest_list, 1):
        name      = quests.quest_config(q)["messages"]["quest_name"]
        reward    = get_reward_name(q)
        task      = get_task_type(q)
        remaining = get_time_remaining(q)
        enrolled  = " [enrolled]" if quests.quest_is_enrolled(q) else ""
        print(f"  {i}. {name:<46} {reward:<36} {task:<22} {remaining}{enrolled}")
    print()


def parse_selection(user_input, total):
    s = user_input.strip().lower()
    if s == "all":
        return list(range(total))
    if s == "none":
        return []
    indices = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            indices.update(range(int(a) - 1, int(b)))
        else:
            indices.add(int(part) - 1)
    return sorted(i for i in indices if 0 <= i < total)


def filter_menu(todo):
    print()
    print("Filter by reward type:")
    print()
    print("  1. Orbs")
    print("  2. Decorations")
    print("  3. All")
    print()
    choice = input("Select filter (1/2/3): ").strip()
    if choice == "1":
        return [q for q in todo if REWARD_TYPE_ORBS in get_reward_types(q)]
    elif choice == "2":
        return [q for q in todo if REWARD_TYPE_DECORATION in get_reward_types(q)]
    else:
        return todo


def run_quest(token, quest):
    qname = quests.quest_config(quest)["messages"]["quest_name"]
    if not quests.quest_is_enrolled(quest):
        is_android = (
            "WATCH_VIDEO_ON_MOBILE" in quests.quest_config(quest)["task_config_v2"]["tasks"]
            and "WATCH_VIDEO" not in quests.quest_config(quest)["task_config_v2"]["tasks"]
        )
        try:
            quests.accept_quest(token, quest, is_android)
        except Exception as e:
            log.error("Failed to enroll in '%s': %s", qname, e)
            return
    else:
        log.info("Already enrolled in '%s'.", qname)
    try:
        tasks.run_task(token, quest)
    except Exception as e:
        log.error("Error completing quest '%s': %s", qname, e)


def auto_completer(token):
    build.update_build_number()

    log.info("Fetching quests...")
    all_quests = quests.fetch_quests(token)
    todo = quests.filter_todo(all_quests)

    filtered = filter_menu(todo)

    if not filtered:
        print("No quests found for that filter.")
        return

    print_quest_list(filtered)

    raw = input("Enter quest numbers to select (e.g. 1,3,5 or 1-5 or 'all' or 'none'): ")
    selected_indices = parse_selection(raw, len(filtered))

    if not selected_indices:
        print("No quests selected.")
        return

    selected = [filtered[i] for i in selected_indices]
    print()
    log.info("Starting %d quest(s)...", len(selected))

    threads = [
        threading.Thread(target=run_quest, args=(token, q), daemon=True)
        for q in selected
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    log.info("All done.")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if len(sys.argv) > 1:
        token = sys.argv[1]
    if not token:
        print("Usage: python main.py <DISCORD_TOKEN>  or  set DISCORD_TOKEN env var")
        sys.exit(1)
    auto_completer(token)