from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(port: int, process: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise AssertionError(f"server exited early\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise AssertionError("server did not become ready")


def http_json(url: str, payload: dict | None = None, expected_status: int = 200) -> dict:
    data = None
    method = "GET"
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        method = "POST"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            if response.status != expected_status:
                raise AssertionError(f"expected status {expected_status}, got {response.status}: {url}")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code != expected_status:
            raise AssertionError(f"expected status {expected_status}, got {exc.code}: {url}\n{body}") from exc
        return json.loads(body)


def require(condition: bool, message: str, detail=None) -> None:
    if not condition:
        raise AssertionError(json.dumps({"message": message, "detail": detail}, ensure_ascii=False, indent=2))


def assert_capabilities(payload: dict) -> None:
    capabilities = payload.get("capabilities") or payload.get("platformCapabilities") or {}
    for key in ("generatedImage", "accounts", "adminStationOutlines", "deployment"):
        require(key in capabilities, f"missing capability {key}", capabilities)
        require("enabled" in capabilities[key], f"capability should expose enabled flag: {key}", capabilities[key])
    require("validation" in capabilities.get("deployment", {}), "deployment capability should expose validation summary", capabilities.get("deployment"))


def main() -> int:
    port = free_port()
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "server.py"), "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        wait_for_server(port, process)
        base = f"http://127.0.0.1:{port}"

        assert_capabilities(http_json(f"{base}/api/capabilities"))
        bootstrap = http_json(f"{base}/api/bootstrap")
        assert_capabilities(bootstrap)
        require("stationMemory" in bootstrap, "bootstrap should expose station memory records", bootstrap.keys())

        identity = http_json(f"{base}/api/identity")
        require(identity.get("ok") is True, "identity endpoint should succeed", identity)
        require(identity.get("identity", {}).get("type") == "anonymous", "identity should be anonymous", identity)
        require(bool(identity.get("identity", {}).get("id")), "identity should include a stable id", identity)

        image_response = http_json(
            f"{base}/api/generated-images",
            {"prompt": "station connection rendering"},
            expected_status=501,
        )
        require(image_response.get("ok") is False, "generated image endpoint should be disabled by default", image_response)
        require(
            image_response.get("error", {}).get("code") == "not_configured",
            "generated image endpoint should return structured not_configured",
            image_response,
        )

        memory_response = http_json(f"{base}/api/station-memory?station=Platform%20Readiness%20HTTP%20Test%20Station")
        require(memory_response.get("ok") is True, "station memory list endpoint should succeed", memory_response)

        station_name = "Platform Readiness HTTP Test Station"
        record_id = "admin-outline-http-test"
        outline_response = http_json(
            f"{base}/api/admin/station-outlines",
            {
                "id": record_id,
                "stationName": station_name,
                "outline": {
                    "id": record_id,
                    "name": "HTTP test station outline",
                    "path": [[120.1, 31.1], [120.2, 31.1], [120.2, 31.2], [120.1, 31.2]],
                },
                "source": {"type": "admin", "operator": "platform-readiness-http-test"},
            },
        )
        require(outline_response.get("ok") is True, "admin outline save should succeed", outline_response)
        require(outline_response.get("record", {}).get("id") == record_id, "admin outline id should round-trip", outline_response)

        query = urlencode({"station": station_name})
        list_response = http_json(f"{base}/api/admin/station-outlines?{query}")
        require(
            any(item.get("id") == record_id for item in list_response.get("records", [])),
            "admin outline should be listed by station",
            list_response,
        )

        apply_response = http_json(
            f"{base}/api/admin/station-outlines/apply",
            {"stationName": station_name, "outlineId": record_id, "geometry": {"stationOutlines": []}},
        )
        require(apply_response.get("ok") is True, "admin outline apply should succeed", apply_response)
        station_outlines = apply_response.get("geometry", {}).get("stationOutlines") or []
        require(station_outlines, "applied geometry should include station outline", apply_response)
        require(
            station_outlines[0].get("source", {}).get("kind") == "admin_station_outline",
            "applied outline should preserve admin source metadata",
            station_outlines[0],
        )
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)

    print("platform readiness HTTP OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
