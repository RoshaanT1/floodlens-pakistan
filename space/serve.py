"""Tiny static server for the FloodLens Space.

Serves ./dist and falls back to index.html for app routes such as /live,
so opening a page address directly still works. /insight and /api are
never rewritten: there is no Insight Agent on the Space, so they 404.
"""
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
PORT = int(os.environ.get("PORT", "7860"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def _route(self):
        path = urlsplit(self.path).path
        if path.startswith(("/insight", "/api")):
            return False
        fs = self.translate_path(path)
        if os.path.isdir(fs):
            fs = os.path.join(fs, "index.html")
        if not os.path.isfile(fs):
            if os.path.splitext(path)[1]:  # a missing file such as a .js or .png
                return False
            self.path = "/index.html"  # an app route: let the React router handle it
        return True

    def do_GET(self):
        if self._route():
            super().do_GET()
        else:
            self.send_error(404)

    def do_HEAD(self):
        if self._route():
            super().do_HEAD()
        else:
            self.send_error(404)

    def end_headers(self):
        path = urlsplit(self.path).path
        if path.startswith("/data/") or path in ("/", "/index.html"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    print(f"Serving {ROOT} on port {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
