import requests
import os

LOCAL_URL = os.environ.get("LOCAL_VAULT_URL", "http://localhost:8000")

def ping_match():
    url = f"{LOCAL_URL}/tasks/match"
    payload = {"description": "I need help with AWS VPC"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        print("Status:", r.status_code)
        print("Response:", r.text)
    except Exception as e:
        print("Bridge Failed:", e)


if __name__ == "__main__":
    ping_match()
