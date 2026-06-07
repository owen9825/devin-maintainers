import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from create_task import create_task
from persistence import get_last_execution_time, set_last_execution_time

from log_config import logger

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = os.environ.get("NVD_API_KEY")
NVD_LISTENER_SLEEP_PERIOD_SECONDS = int(
    os.environ.get("NVD_LISTENER_SLEEP_PERIOD_SECONDS", 300)
)

_MODULE_NAME = Path(__file__).stem

def get_vulnerabilities(last_run: Optional[int]):
    params = {}
    if last_run:
        fmt = "%Y-%m-%dT%H:%M:%S.000"
        params["lastModStartDate"] = datetime.fromtimestamp(last_run, tz=timezone.utc).strftime(fmt)
        params["lastModEndDate"] = datetime.now(tz=timezone.utc).strftime(fmt)

    headers = {"apiKey": NVD_API_KEY} if NVD_API_KEY else {}

    resp = requests.get(NVD_API, params=params, headers=headers)
    resp.raise_for_status()

    return [entry["cve"] for entry in resp.json().get("vulnerabilities", [])]

if __name__ == "__main__":
    while True:
        last_run = get_last_execution_time(_MODULE_NAME)
        logger.info(f"Waking. The last execution time was {last_run}")
        vulnerabilities = get_vulnerabilities(last_run)
        for vulnerability in vulnerabilities:
            cve_id = vulnerability["id"]
            notes = next(
                (d["value"] for d in vulnerability.get("descriptions", []) if d["lang"] == "en"),
                "",
            )
            logger.info(f"There is a bug: {cve_id} (published {vulnerability['published']})")
            create_task(title=cve_id, worker="nvd_listener", notes=notes)

        set_last_execution_time(_MODULE_NAME, int(time.time()))
        time.sleep(NVD_LISTENER_SLEEP_PERIOD_SECONDS)
