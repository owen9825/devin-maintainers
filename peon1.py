import os
import time
import requests

API_KEY = os.environ["DEVIN_API_KEY"]
ORG_ID = os.environ["DEVIN_ORG_ID"]
BASE = "https://api.devin.ai/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
SELF_ID = os.environ["SELF_USER_ID"]

# 1. Verify credentials
me = requests.get(f"{BASE}/self", headers=HEADERS)
me.raise_for_status()
data = me.json()
print(f"Authenticated as: {data.get('service_user_name') or data.get('user_name')}")

# 2. Create a session
session = requests.post(
    f"{BASE}/organizations/{ORG_ID}/sessions",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={"prompt": "Create a Python script that analyzes CSV data", "create_as_user_id": SELF_ID}
).json()
print(f"Session: {session['url']}")

# 3. Poll until complete
while True:
    status = requests.get(
        f"{BASE}/organizations/{ORG_ID}/sessions/{session['session_id']}",
        headers=HEADERS
    ).json()["status"]
    print(f"Status: {status}")
    if status in ("exit", "error", "suspended"):
        break
    time.sleep(10)

