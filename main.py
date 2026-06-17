import os
import sys
import logging

import src.build as build
import src.rest as rest
import src.quests as quests
import src.tasks as tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def auto_completer(token):
    build.update_build_number()

    log.info("Fetching quests...")
    all_quests = quests.fetch_quests(token)

    todo = quests.filter_todo(all_quests)
    log.info("Found %d quest(s) to complete.", len(todo))

    for quest in todo:
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
                continue
        else:
            log.info("Already enrolled in '%s'.", qname)

        try:
            tasks.run_task(token, quest)
        except Exception as e:
            log.error("Error completing quest '%s': %s", qname, e)

    log.info("All done.")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if len(sys.argv) > 1:
        token = sys.argv[1]
    if not token:
        print("Usage: python main.py <DISCORD_TOKEN>  or  set DISCORD_TOKEN env var")
        sys.exit(1)
    auto_completer(token)
