from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_health_server(port: int) -> HTTPServer:
    server = HTTPServer(('', port), HealthHandler)
    server.is_up = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server