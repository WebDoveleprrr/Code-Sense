import requests
import json

repo_id = "6a093ba7241c7b258ee92ccb"

try:
    print("Testing Architecture...")
    res1 = requests.get(f"http://localhost:8000/api/v1/architecture/{repo_id}")
    print("Status:", res1.status_code)
    try:
        print("Data:", json.dumps(res1.json())[:200], "...")
    except Exception as e:
        print("Raw response:", res1.text[:200])
except Exception as e:
    print("Architecture failed:", e)

try:
    print("\nTesting Explain...")
    res2 = requests.post("http://localhost:8000/api/v1/explain", json={
        "repo_id": repo_id,
        "file_path": "main.py",
        "start_line": 1,
        "end_line": 50
    })
    print("Status:", res2.status_code)
    try:
        print("Data:", json.dumps(res2.json())[:200], "...")
    except Exception as e:
        print("Raw response:", res2.text[:200])
except Exception as e:
    print("Explain failed:", e)
