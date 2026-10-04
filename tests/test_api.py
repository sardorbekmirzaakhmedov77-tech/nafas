from nafas.collector import parse_hourly


def test_cities_list(client):
    data = client.get("/api/v1/cities").get_json()
    assert len(data["cities"]) == 14
    tashkent = next(c for c in data["cities"] if c["slug"] == "tashkent")
    assert "us_aqi" in tashkent["current"]


def test_city_detail_and_unknown_city(client):
    assert client.get("/api/v1/cities/samarkand").status_code == 200
    resp = client.get("/api/v1/cities/atlantis")
    assert resp.status_code == 404
    assert "Unknown city" in resp.get_json()["error"]


def test_history_respects_hours_and_limits(client):
    data = client.get("/api/v1/cities/tashkent/history?hours=48").get_json()
    assert len(data["readings"]) == 48
    capped = client.get("/api/v1/cities/tashkent/history?hours=99999").get_json()
    assert capped["hours"] == 24 * 31
    assert client.get("/api/v1/cities/tashkent/history?hours=abc").status_code == 400


def test_forecast_is_in_the_future(client):
    data = client.get("/api/v1/cities/bukhara/forecast").get_json()
    current = client.get("/api/v1/cities/bukhara").get_json()["current"]["time"]
    assert data["hourly"] and all(h["time"] > current for h in data["hourly"])
    assert data["daily"]


def test_parse_open_meteo_payload():
    payload = {"hourly": {
        "time": ["2026-10-05T00:00", "2026-10-05T01:00"],
        "us_aqi": [42.4, None], "pm2_5": [8.1, 9.3], "pm10": [20, 22],
    }}
    rows = parse_hourly(payload)
    assert rows[0]["us_aqi"] == 42 and rows[1]["us_aqi"] is None
    assert rows[1]["pm2_5"] == 9.3 and rows[0]["ozone"] is None


def test_pages_render(client):
    for path in ("/", "/?city=nukus", "/city/tashkent", "/about", "/developers",
                 "/login", "/register"):
        assert client.get(path).status_code == 200, path
    assert client.get("/city/nowhere").status_code == 404


def test_register_watch_and_csrf(client):
    client.get("/register")
    with client.session_transaction() as sess:
        token = sess["_csrf"]
    # Missing token is rejected
    assert client.post("/register", data={"name": "A", "email": "a@b.co",
                                          "password": "longpassword"}).status_code == 400
    resp = client.post("/register", data={"_csrf": token, "name": "Aziza",
                                          "email": "aziza@example.com", "password": "longpassword"})
    assert resp.status_code == 302
    resp = client.post("/alerts/watch", data={"_csrf": token, "city": "tashkent", "threshold": "151"},
                       follow_redirects=True)
    assert b"Watching Tashkent" in resp.data
    assert client.get("/alerts/").status_code == 200
