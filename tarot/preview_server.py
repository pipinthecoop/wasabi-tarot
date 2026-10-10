"""Read-only loopback asset/demo host. No secrets, Slack ingress, DB, or worker."""

import ipaddress
import json
import mimetypes
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def handler(root: Path) -> type[BaseHTTPRequestHandler]:
    public = {"/table": root / "web/table.html", "/": root / "web/table.html", "/embed/table": root / "web/table.html"}
    public["/decks"] = root / "web/gallery.html"
    public["/decks/crt"] = root / "web/gallery.html"
    for name in ("table.css", "table.js", "demo.json", "gallery.css", "gallery.js"):
        public["/web/" + name] = root / "web" / name
    for file in (root / "art/theme").glob("*"):
        if file.suffix in (".png", ".webp"):
            public["/assets/theme/" + file.name] = file
    for deck in ("dawn", "midnight", "crt"):
        for file in (root / "art" / deck).glob("*"):
            if file.suffix in (".png", ".gif"):
                public[f"/assets/decks/{deck}/{file.name}"] = file

    class Preview(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            # No request bodies, tokens, query strings or reader prompts in logs.
            return

        def reply(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "public, max-age=300")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: data:; frame-ancestors 'self'; base-uri 'none'",
            )
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self) -> None:
            path = urllib.parse.urlsplit(self.path).path
            if path == "/health":
                self.reply(
                    200,
                    json.dumps({"status": "ok", "mode": "asset-demo-only", "slack_ingress": False, "worker": False, "database": False}).encode(),
                    "application/json",
                )
                return
            if path == "/api/table":
                self.reply(401, b'{"error":"Demo host: live Slack table is disabled"}', "application/json")
                return
            file = public.get(path)
            if not file or not file.is_file():
                self.reply(404, b"Not found", "text/plain")
                return
            body = file.read_bytes()
            if file.name == "table.html":
                body = body.replace(b"Isolated demo", b"Asset/demo host: Slack ingress and worker disabled")
            self.reply(200, body, mimetypes.guess_type(file.name)[0] or "application/octet-stream")

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_POST(self) -> None:
            self.reply(405, b'{"error":"Read-only demo host; Slack ingress and live actions are disabled"}', "application/json")

    return Preview


def address() -> tuple[str, int]:
    host = os.environ.get("BIND_HOST", "127.0.0.1")
    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError("The no-secret preview host must bind to a loopback address")
    port = int(os.environ.get("PORT", "8765"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be 1–65535")
    return host, port


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    host, port = address()
    server = ThreadingHTTPServer((host, port), handler(root))
    print(f"Wasabi Tarot asset/demo-only host on {host}:{port}; Slack ingress, credentials, database and worker disabled.", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
