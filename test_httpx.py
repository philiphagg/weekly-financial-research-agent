import httpx

url = "http://192.168.1.71:8080/api/v1/signals"
params = {"status": "ACTIVE", "assetType": "stock"}

with httpx.Client(timeout=20.0, trust_env=False) as client:
    r = client.get(url, params=params)
    print(r.status_code)
    print(r.text[:500])