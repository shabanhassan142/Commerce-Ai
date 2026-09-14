import urllib.request, json

BASE = "http://127.0.0.1:8000"
LOGIN_URL = BASE + "/api/v1/auth/login"

def test_login(email, password, label):
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(LOGIN_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            user = body["data"]["user"]
            tok = body["data"]["tokens"]["access_token"]
            print(f"[OK] {label}: status={r.status}, email={user['email']}, role={user['role']}, token={tok[:20]}...")
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f"[FAIL] {label}: HTTP {e.code} -> {err}")
    except Exception as ex:
        print(f"[ERROR] {label}: {ex}")

test_login("admin@commerceflow.ai", "Admin123!", "Admin")
test_login("support@commerceflow.ai", "Support123!", "Support")
test_login("customer1@example.com", "Customer123!", "Customer")
test_login("shabanhassan142@gmail.com", "Shaban123!", "Shaban (registered earlier)")
