"""
`waiting_for` is served from a python http server.

Another way of serving it is with nginx and a static file, but then stale data could be served.
Instead, when the python process ends, no waiting_for will be served.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


class WaitingForHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        waiting_for = self.server.repo_waiting.get(self.path.lstrip('/'))
        if waiting_for:
            self.send_response_only(200)
            self.end_headers()
            self.wfile.write(waiting_for.encode('utf-8'))
        else:
            self.send_response_only(404)
            self.end_headers()

    def log_message(self, *args):
        pass  # Discard


class HttpServer(Thread):
    def __init__(self):
        super().__init__(daemon=True, name='HttpServerThread')

        # Accessible from LAN. Assumes noone will DoS it. Not to be exposed to internet.
        host = '0.0.0.0'
        self.server = HTTPServer((host, 8087), WaitingForHandler)

        self.repo_waiting = self.server.repo_waiting = {}
        self.start()

    def run(self):
        self.server.serve_forever()
