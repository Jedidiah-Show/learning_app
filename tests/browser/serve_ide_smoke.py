"""Serve the real static IDE runner with its production CORP policy."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Resource-Policy', 'cross-origin')
        if self.path.startswith('/static/pyodide/'):
            self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


ThreadingHTTPServer(('127.0.0.1', 4173), Handler).serve_forever()
