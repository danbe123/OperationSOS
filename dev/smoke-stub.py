"""Tiny stand-in for the dev stack used by dev/smoke-selftest.sh: `python3 dev/smoke-stub.py good|broken PORT`.
In `broken` mode /api/search answers 500 and the captive-portal probe answers 204 instead of 302."""
import http.server
import sys

MODE = sys.argv[1]
PORT = int(sys.argv[2])
BOOK = "wikipedia_en_100_mini_2026-01"
ROUTES = {
    "/api/status": (200, b'{"version":"0.1.0","dev":true}'),
    "/api/library": (200, b'{"categories":[]}'),
    "/api/search?q=water": (200, b'{"q":"water","results":[],"partial":false}'),
    "/api/suggest?q=wat": (200, b"[]"),
    f"/kiwix/content/{BOOK}/": (302, f"/kiwix/content/{BOOK}/index"),
    f"/kiwix/content/{BOOK}/index": (200, b"<html><body>stub article</body></html>"),
    "/welcome": (200, b"<html><body>Open http://10.42.0.1 in your browser (or http://sos.box)</body></html>"),
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/generate_204":
            if MODE == "broken":
                self.send_response(204)
                self.end_headers()
                return
            self.send_response(302)
            self.send_header("Location", "http://10.42.0.1/welcome")
            self.end_headers()
            return
        code, body = ROUTES.get(self.path, (404, b"not found"))
        if MODE == "broken" and self.path == "/api/search?q=water":
            code, body = 500, b"boom"
        if code == 302:
            self.send_response(302)
            self.send_header("Location", body)
            self.end_headers()
            return
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
