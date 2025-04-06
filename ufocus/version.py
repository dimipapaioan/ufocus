import json
import logging
import urllib.error
import urllib.request

APP_GH_API_URL = "https://api.github.com/repos/dimipapaioan/ufocus/releases/latest"
VERSION_INFO = (2, 3, 2)


logger = logging.getLogger(__name__)


def get_version() -> str:
    return ".".join(map(str, VERSION_INFO))


def get_latest_version() -> tuple[str | None, str | None]:
    try:
        with urllib.request.urlopen(APP_GH_API_URL) as response:
            # Read the response and decode it
            data = response.read().decode()

            # Parse the response as JSON
            release_info: dict[str, str] = json.loads(data)

    except urllib.error.HTTPError as err:
        logger.error(f"HTTP Error: {err.code} - {err.reason}")
        return None, None

    except urllib.error.URLError as err:
        logger.error(f"URL Error: {err.reason}")
        return None, None

    except Exception as e:
        logger.exception(f"Error: {str(e)}")
        return None, None

    else:
        latest_version = release_info.get("tag_name", None)
        if latest_version is not None:
            latest_version = latest_version.replace("v", "")

        release_date = release_info.get("published_at", None)
        return latest_version, release_date
