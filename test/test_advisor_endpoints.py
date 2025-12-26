import sqlite3
import requests
import pytest

DB_PATH = "mondrian.db"
BASE_URL = "http://127.0.0.1:5005"


def get_advisor_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM advisors")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


@pytest.mark.parametrize("advisor_id", get_advisor_ids())
def test_advisor_endpoint_returns_expected_json(advisor_id):
    url = f"{BASE_URL}/advisor/{advisor_id}"
    try:
        r = requests.get(url, timeout=5, headers={"Accept": "application/json"})
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Server not available or network error: {e}")

    assert r.status_code == 200, f"Expected 200 for {advisor_id}, got {r.status_code} - body: {r.text}"

    data = r.json()
    # Basic required fields
    assert data.get("id") == advisor_id
    assert "name" in data and data.get("name")
    assert "bio" in data
    assert "image_url" in data
    assert "work_examples" in data and isinstance(data.get("work_examples"), list)
