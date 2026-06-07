import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from persistence import get_last_execution_time, set_last_execution_time

from log_config import logger

CVE_MITRE_API = "https://cveawg.mitre.org/api/cves"
CVE_MITRE_LISTENER_SLEEP_PERIOD_SECONDS = int(
    os.environ.get("CVE_MITRE_LISTENER_SLEEP_PERIOD_SECONDS", 300)
)

_MODULE_NAME = Path(__file__).stem


def get_cves(last_run: Optional[int]) -> list:
    params = {"state": "PUBLISHED"}
    if last_run:
        since = datetime.fromtimestamp(last_run, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        params["dateUpdatedAfter"] = since
    resp = requests.get(CVE_MITRE_API, params=params)
    resp.raise_for_status()
    return [cve.get("cveMetadata", {}) for cve in resp.json().get("cves", [])]


if __name__ == "__main__":
    while True:
        last_run = get_last_execution_time(_MODULE_NAME)
        logger.info(f"Waking. The last execution time was {last_run}")
        for meta in get_cves(last_run):
            logger.info(f"There is a bug: {meta.get('cveId')} (published {meta.get('datePublished')})")
        set_last_execution_time(_MODULE_NAME, int(time.time()))
        time.sleep(CVE_MITRE_LISTENER_SLEEP_PERIOD_SECONDS)
