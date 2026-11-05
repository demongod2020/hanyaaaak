"""Run against a live local server; no additional testing packages required."""
import json
from urllib.error import HTTPError
from urllib.request import urlopen

BASE = "http://127.0.0.1:8000"


def get(path):
    with urlopen(BASE + path, timeout=10) as response:
        assert response.status == 200, path
        return response.read()


assert json.loads(get("/api/health")) == {
    "status": "ok", "service": "bonchorok", "herb_count": 601
}
records = json.loads(get("/herbs.json"))
assert len(records) == 601
assert len({r["id"] for r in records}) == len(records)
assert any(r["id"] == "sophorae-flos" for r in records)
assert b"app-v2.js" in get("/?herb=sophorae-flos")
for asset in ["/details.js", "/style.css", "/sophora-plant.jpg"]:
    assert get(asset)
assert "/api/health" in json.loads(get("/openapi.json"))["paths"]
assert b"swagger" in get("/docs").lower()
for private_path in ["/main.py", "/requirements.txt", "/.git/config", "/../README.md"]:
    try:
        get(private_path)
    except HTTPError as error:
        assert error.code == 404, (private_path, error.code)
    else:
        raise AssertionError(f"Private file was exposed: {private_path}")
print("PASS: health, 601 herbs, app assets, API docs and private-file protection")
