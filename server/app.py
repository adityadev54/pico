"""Local scaffold only. No authenticated or computer-control endpoints yet."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "contract-examples.json"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            data = {"status": "ok", "mode": "scaffold", "meta_connected": False,
                    "device_connected": False, "execution_available": False}
            status = 200
        elif self.path == "/contracts":
            data = json.loads(CONTRACT.read_text())
            status = 200
        else:
            data, status = {"error": "not_found"}, 404
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    print("Pico scaffold: http://127.0.0.1:8000 (local only)")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
