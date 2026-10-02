from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os, webbrowser

os.chdir(Path(__file__).resolve().parent)
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/': self.path = '/live.html'
        super().do_GET()
    def log_message(self, *_): pass

for port in range(8787, 8807):
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        break
    except OSError:
        continue
else:
    raise SystemExit('No available local port')
url = f'http://127.0.0.1:{port}/live.html'
print(f'FC AI Live: {url}\nKeep this terminal open. Ctrl+C to stop.', flush=True)
webbrowser.open(url)
try: server.serve_forever()
except KeyboardInterrupt: pass
finally: server.server_close()
