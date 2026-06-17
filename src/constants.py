import uuid

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9236 Chrome/138.0.7204.251 "
    "Electron/37.6.0 Safari/537.36"
)
ANDROID_USER_AGENT = "Discord-Android/316011;RNA"
DISCORD_API = "https://discord.com/api/v10"


def random_uuid():
    return str(uuid.uuid4())


def desktop_properties(build_number=539951):
    return {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": "1.0.9236",
        "os_version": "10.0.19045",
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "has_client_mods": False,
        "client_launch_id": random_uuid(),
        "browser_user_agent": USER_AGENT,
        "browser_version": "37.6.0",
        "os_sdk_version": "19045",
        "client_build_number": build_number,
        "native_build_number": 81687,
        "client_event_source": None,
        "launch_signature": random_uuid(),
        "client_heartbeat_session_id": random_uuid(),
        "client_app_state": "focused",
    }


def android_properties():
    return {
        "os": "Android",
        "browser": "Discord Android",
        "device": "b0q",
        "system_locale": "en-US",
        "has_client_mods": False,
        "client_version": "316.11 - rn",
        "release_channel": "googleRelease",
        "device_vendor_id": random_uuid(),
        "design_id": 2,
        "browser_user_agent": "",
        "browser_version": "",
        "os_version": "28",
        "client_build_number": 5169,
        "client_event_source": None,
        "client_launch_id": random_uuid(),
        "launch_signature": "1771754995045142953",
        "client_app_state": "active",
        "client_heartbeat_session_id": random_uuid(),
    }
