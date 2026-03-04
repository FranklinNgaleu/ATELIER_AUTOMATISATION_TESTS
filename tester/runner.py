from datetime import datetime, timezone
from tester.client import ApiClient
from tester.tests import run_tests
from storage import save_run


BASE_URL = "https://api.citybik.es/v2"


def _utc_iso():
    return datetime.now(timezone.utc).isoformat()


def _p95(values):
    xs = sorted([v for v in values if v is not None])
    if not xs:
        return None
    # nearest-rank p95
    k = int((0.95 * len(xs)) + 0.999999)  # ceil
    k = min(max(k, 1), len(xs))
    return xs[k - 1]


def compute_metrics(checks):
    latencies = [c.get("latency_ms") for c in checks if c.get("latency_ms") is not None]
    avg = (sum(latencies) / len(latencies)) if latencies else None
    p95 = _p95(latencies)

    total = len(checks)
    errors = sum(1 for c in checks if not c["ok"])
    error_rate = (errors / total) if total else None

    return {"lat_avg_ms": avg, "lat_p95_ms": p95, "error_rate": error_rate}


def main():
    api = ApiClient(BASE_URL, timeout_s=5.0, max_retries=2)

    started_at = _utc_iso()
    checks = run_tests(api)
    finished_at = _utc_iso()

    metrics = compute_metrics(checks)
    ok = all(c["ok"] for c in checks)

    run = {
        "started_at": started_at,
        "finished_at": finished_at,
        "ok": ok,
        "metrics": metrics,
        "checks": checks,
    }
    run_id = save_run(run)
    print(f"run_id={run_id} ok={ok} total={len(checks)} errors={sum(1 for c in checks if not c['ok'])}")


if __name__ == "__main__":
    main()