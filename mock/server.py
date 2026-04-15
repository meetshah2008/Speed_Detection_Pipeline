from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode()

        print("ALERT RECEIVED:", self.path)
        print("BODY:", body)

        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), H)
    print("Server running on http://0.0.0.0:8000")
    server.serve_forever()
