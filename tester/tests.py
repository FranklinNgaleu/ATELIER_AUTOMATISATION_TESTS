def _is_num(x):
    return isinstance(x, (int, float))


def assert_location(loc: dict):
    assert isinstance(loc, dict)
    assert "city" in loc and isinstance(loc["city"], str)
    assert "country" in loc and isinstance(loc["country"], str)
    assert "latitude" in loc and _is_num(loc["latitude"])
    assert "longitude" in loc and _is_num(loc["longitude"])


def assert_station(s: dict):
    assert isinstance(s, dict)
    for k in ["id", "name", "latitude", "longitude"]:
        assert k in s
    assert isinstance(s["id"], str) and s["id"]
    assert isinstance(s["name"], str)
    assert _is_num(s["latitude"])
    assert _is_num(s["longitude"])

    # Champs souvent présents mais pas garantis partout
    if "free_bikes" in s:
        assert isinstance(s["free_bikes"], (int, type(None)))
    if "empty_slots" in s:
        assert isinstance(s["empty_slots"], (int, type(None)))
    if "timestamp" in s:
        assert isinstance(s["timestamp"], str)


def assert_network_detail(payload: dict):
    assert isinstance(payload, dict)
    assert "network" in payload and isinstance(payload["network"], dict)
    n = payload["network"]

    for k in ["id", "name", "href", "location"]:
        assert k in n

    assert isinstance(n["id"], str) and n["id"]
    assert isinstance(n["name"], str)
    assert isinstance(n["href"], str) and n["href"].startswith("/v2/networks/")
    assert_location(n["location"])

    if "company" in n:
        assert isinstance(n["company"], (str, list))

    if "stations" in n:
        assert isinstance(n["stations"], list)
        if len(n["stations"]) > 0:
            assert_station(n["stations"][0])


def run_tests(api):
    """
    Execute a fixed test suite (<=20 requests/run).
    Returns a list of check results dicts.
    """
    checks = []

    def add_check(name, method, path, params, expected_status, validate_fn=None, expected_error=False):
        resp, latency_ms, err = api.request(method, path, params=params)

        result = {
            "name": name,
            "method": method,
            "path": path if not params else f"{path}?{_fmt_params(params)}",
            "status_code": None,
            "latency_ms": latency_ms,
            "ok": False,
            "error_type": None,
            "error_message": None,
        }

        if err is not None:
            result["error_type"] = err["type"]
            result["error_message"] = err["message"]
            checks.append(result)
            return

        result["status_code"] = resp.status_code

        try:
            assert resp.status_code == expected_status

            if validate_fn is not None and not expected_error:
                data = resp.json()
                validate_fn(data)

            result["ok"] = True

        except Exception as e:
            result["ok"] = False
            result["error_type"] = type(e).__name__
            result["error_message"] = str(e)[:500]

        checks.append(result)

    # 8 requêtes/run (rythme raisonnable)
    add_check(
        name="networks_light",
        method="GET",
        path="/networks",
        params={"fields": "id,name,href"},
        expected_status=200,
        validate_fn=_validate_networks_light,
    )
    add_check(
        name="networks_ids_only",
        method="GET",
        path="/networks",
        params={"fields": "id"},
        expected_status=200,
        validate_fn=_validate_networks_ids_only,
    )
    add_check(
        name="velib_full",
        method="GET",
        path="/networks/velib",
        params=None,
        expected_status=200,
        validate_fn=assert_network_detail,
    )
    add_check(
        name="velib_stations_only",
        method="GET",
        path="/networks/velib",
        params={"fields": "stations"},
        expected_status=200,
        validate_fn=_validate_stations_only,
    )
    add_check(
        name="velib_core_fields",
        method="GET",
        path="/networks/velib",
        params={"fields": "id,name,href,location"},
        expected_status=200,
        validate_fn=_validate_network_core_fields,
    )
    add_check(
        name="404_expected",
        method="GET",
        path="/networks/does-not-exist-zzz",
        params=None,
        expected_status=404,
        validate_fn=None,
        expected_error=True,
    )
    # 2 répétitions (stabilise avg/p95)
    add_check(
        name="velib_repeat_1",
        method="GET",
        path="/networks/velib",
        params={"fields": "id"},
        expected_status=200,
        validate_fn=_validate_network_id_only,
    )
    add_check(
        name="velib_repeat_2",
        method="GET",
        path="/networks/velib",
        params={"fields": "id"},
        expected_status=200,
        validate_fn=_validate_network_id_only,
    )

    return checks


def _fmt_params(params: dict) -> str:
    # affichage lisible dans le dashboard (pas besoin d'encodage strict)
    return "&".join([f"{k}={v}" for k, v in params.items()])


def _validate_networks_light(payload: dict):
    assert isinstance(payload, dict)
    assert "networks" in payload and isinstance(payload["networks"], list)
    assert len(payload["networks"]) > 0
    item = payload["networks"][0]
    assert "id" in item and isinstance(item["id"], str)
    assert "name" in item and isinstance(item["name"], str)
    assert "href" in item and isinstance(item["href"], str)


def _validate_networks_ids_only(payload: dict):
    assert isinstance(payload, dict)
    assert "networks" in payload and isinstance(payload["networks"], list)
    assert len(payload["networks"]) > 0
    item = payload["networks"][0]
    assert "id" in item and isinstance(item["id"], str)


def _validate_stations_only(payload: dict):
    assert isinstance(payload, dict)
    assert "network" in payload and isinstance(payload["network"], dict)
    n = payload["network"]
    assert "stations" in n and isinstance(n["stations"], list)
    if len(n["stations"]) > 0:
        assert_station(n["stations"][0])


def _validate_network_core_fields(payload: dict):
    assert isinstance(payload, dict)
    assert "network" in payload and isinstance(payload["network"], dict)
    n = payload["network"]
    for k in ["id", "name", "href", "location"]:
        assert k in n
    assert isinstance(n["id"], str)
    assert isinstance(n["name"], str)
    assert isinstance(n["href"], str)
    assert_location(n["location"])


def _validate_network_id_only(payload: dict):
    assert isinstance(payload, dict)
    assert "network" in payload and isinstance(payload["network"], dict)
    n = payload["network"]
    assert "id" in n and isinstance(n["id"], str)