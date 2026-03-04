import time
import random
import requests


class ApiClient:
    def __init__(self, base_url: str, timeout_s: float = 5.0, max_retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.session = requests.Session()

    def request(self, method: str, path: str, *, params=None):
        """
        Returns: (resp | None, latency_ms | None, error_dict | None)
        error_dict example: {"type": "Timeout", "message": "..."}
        """
        url = f"{self.base_url}{path}"
        attempt = 0

        while attempt <= self.max_retries:
            attempt += 1
            start = time.perf_counter()

            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout_s,
                    headers={"Accept": "application/json"},
                )
                latency_ms = (time.perf_counter() - start) * 1000.0

                # Rate limit
                if resp.status_code == 429 and attempt <= self.max_retries:
                    ra = resp.headers.get("Retry-After")
                    sleep_s = float(ra) if (ra and ra.isdigit()) else (0.5 * attempt)
                    time.sleep(min(sleep_s, 5.0))
                    continue

                # Server errors
                if 500 <= resp.status_code <= 599 and attempt <= self.max_retries:
                    time.sleep(min(0.5 * attempt + random.random() * 0.2, 2.0))
                    continue

                return resp, latency_ms, None

            except (requests.Timeout, requests.ConnectionError) as e:
                latency_ms = (time.perf_counter() - start) * 1000.0
                if attempt <= self.max_retries:
                    time.sleep(min(0.5 * attempt + random.random() * 0.2, 2.0))
                    continue
                return None, latency_ms, {"type": type(e).__name__, "message": str(e)[:500]}

            except Exception as e:
                latency_ms = (time.perf_counter() - start) * 1000.0
                return None, latency_ms, {"type": type(e).__name__, "message": str(e)[:500]}

        return None, None, {"type": "UnknownError", "message": "Unexpected loop exit"}