import json
import os
import socket

BASE = os.path.dirname(os.path.abspath(__file__))

def parse_request(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(1024)
        if not chunk:
            return None
        data += chunk
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.decode().split("\r\n")
    method, target, _ = lines[0].split(" ")
    headers = {}
    for line in lines[1:]:
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    length = int(headers.get("content-length", 0))
    while len(body) < length:
        body += conn.recv(1024)
    path, _, qs = target.partition("?")
    query = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
    return method, path, query, headers, body


def response(status, body, content_type="text/html"):
    if isinstance(body, str):
        body = body.encode()
    head = (f"HTTP/1.1 {status}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n")
    return head.encode() + body

def handle(method, path, query, headers, body):
    if method == "GET":
        if path == "/page":
            return response("200 OK", f"<h1>Page {query.get('id')}</h1>")
        if path == "/headers":
            return response("200 OK", json.dumps(headers), "application/json")
        file = os.path.join(BASE, "static", "index.html" if path == "/" else path.lstrip("/"))
        if ".." not in path and os.path.isfile(file):
            content_type = "text/css" if file.endswith(".css") else "text/html"
            with open(file, "rb") as f:
                return response("200 OK", f.read(), content_type)
        return response("404 Not Found", "Not Found")
    if method == "POST" and path == "/api/echo":
        try:
            data = json.loads(body)
        except ValueError:
            return response("400 Bad Request", '{"error": "Invalid JSON"}', "application/json")
        return response("200 OK", json.dumps({"received": data}), "application/json")
    return response("405 Method Not Allowed", "Method Not Allowed")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("", 8080))
server.listen()
print("Server running on http://localhost:8080")

while True:
    conn, _ = server.accept()
    with conn:
        try:
            request = parse_request(conn)
            if request:
                conn.sendall(handle(*request))
        except Exception:
            conn.sendall(response("400 Bad Request", "Bad Request"))