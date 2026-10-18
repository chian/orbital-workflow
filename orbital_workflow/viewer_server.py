"""Local run catalog and on-demand numerical reads with bounded payload caches."""

from collections import OrderedDict
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit

from .storage import identifier, read_observation, read_forcing
from .visualization import load_catalog, render_document


def run_signature(directory):
    paths = [directory / "summary.json", directory / "manifest.json",
             directory / "episode-store" / "format.json"]
    paths.extend((directory / "episode-store" / "index").glob("*.json"))
    paths.extend((directory / "episode-store" / "ownership").glob("*/*.json"))
    paths.extend((directory / "episode-store" / "episodes").glob("*/manifest.json"))
    result = []
    for path in sorted(paths):
        try:
            info = path.stat()
            result.append((str(path.relative_to(directory)), info.st_mtime_ns, info.st_size))
        except FileNotFoundError:
            pass
    return tuple(result)


class ViewerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, directory, *, port=8767, cache_bytes=16 * 1024 * 1024):
        self.default_directory = Path(directory).resolve()
        self.snapshots, self.observations = OrderedDict(), OrderedDict()
        self.cache_lock = threading.Lock()
        self.cache_budget = cache_bytes
        self.observation_bytes = 0
        super().__init__(("127.0.0.1", port), ViewerRequest)

    def snapshot(self, directory):
        directory = Path(directory).resolve()
        signature = run_signature(directory)
        with self.cache_lock:
            cached = self.snapshots.get(directory)
            if cached is None or cached["signature"] != signature:
                data = load_catalog(directory)
                data["live"] = {"endpoint": "/api/snapshot", "data_endpoint": "/api/observation",
                                "forcing_endpoint": "/api/forcing", "interval_ms": 2000,
                                "browser_cache_bytes": 16 * 1024 * 1024}
                payload = json.dumps(data, separators=(",", ":"), allow_nan=False).encode()
                cached = {"signature": signature, "data": data, "payload": payload,
                          "etag": '"' + sha256(payload).hexdigest() + '"'}
                if len(payload) <= self.cache_budget:
                    self.snapshots[directory] = cached
                    self.snapshots.move_to_end(directory)
                while len(self.snapshots) > 4 or sum(len(item["payload"]) for item in self.snapshots.values()) > self.cache_budget:
                    self.snapshots.popitem(last=False)
            return cached

    def observation(self, directory, identity, start=None, end=None):
        directory = Path(directory).resolve()
        path = directory / "episode-store" / "observations" / identifier(identity) / "manifest.json"
        key = (str(directory), identity, path.stat().st_mtime_ns, start, end)
        with self.cache_lock:
            if key in self.observations:
                self.observations.move_to_end(key)
                return self.observations[key]
            packet = read_observation(directory, identity, start=start, end=end)
            payload = json.dumps(packet, separators=(",", ":"), allow_nan=False).encode()
            if len(payload) <= self.cache_budget:
                self.observations[key] = payload
                self.observation_bytes += len(payload)
                while self.observation_bytes > self.cache_budget:
                    _, old = self.observations.popitem(last=False)
                    self.observation_bytes -= len(old)
            return payload


class ViewerRequest(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        target = urlsplit(self.path)
        if target.path not in ("/", "/api/snapshot", "/api/observation", "/api/forcing", "/health"):
            self.send_error(404)
            return
        if target.path == "/health":
            self.respond(200, json.dumps({
                "viewer": "orbital-workflow", "default_run": str(self.server.default_directory),
                "cached_observation_payloads": len(self.server.observations),
                "observation_cache_bytes": self.server.observation_bytes,
                "observation_cache_budget": self.server.cache_budget,
                "catalog_contains_arrays": False,
            }).encode(), "application/json")
            return
        query = parse_qs(target.query)
        directory = Path(query.get("run", [str(self.server.default_directory)])[0]).expanduser()
        try:
            if target.path == "/api/observation":
                start = float(query["start"][0]) if "start" in query else None
                end = float(query["end"][0]) if "end" in query else None
                self.respond(200, self.server.observation(directory, query["id"][0], start, end), "application/json")
                return
            if target.path == "/api/forcing":
                result = read_forcing(directory, query["id"][0], float(query.get("time", [0])[0]))
                self.respond(200, json.dumps(result, separators=(",", ":"), allow_nan=False).encode(), "application/json")
                return
            snapshot = self.server.snapshot(directory)
            if target.path == "/api/snapshot":
                if self.headers.get("If-None-Match") == snapshot["etag"]:
                    self.send_response(304)
                    self.send_header("ETag", snapshot["etag"])
                    self.end_headers()
                    return
                self.respond(200, snapshot["payload"], "application/json", snapshot["etag"])
            else:
                self.respond(200, render_document(snapshot["data"]).encode(), "text/html; charset=utf-8")
        except (OSError, ValueError, KeyError) as error:
            self.respond(503, json.dumps({"error": type(error).__name__, "message": str(error)}).encode(), "application/json")

    def respond(self, status, payload, content_type, etag=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        if etag:
            self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(payload)


def serve_viewer(directory, *, port=8767):
    server = ViewerServer(directory, port=port)
    host, actual_port = server.server_address
    print(json.dumps({"url": f"http://{host}:{actual_port}/",
                      "run": str(server.default_directory),
                      "mode": "live catalog + on-demand episode-store reads"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
