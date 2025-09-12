import asyncio
import websockets
import websockets.exceptions
from websockets.asyncio.server import serve
import http.server
import socketserver
import threading
import qrcode
import os
import socket
from urllib.parse import urlparse

HOST = "0.0.0.0"        # Listen on all interfaces
PORT = 8765             # WebSocket port
HTTP_PORT = 8000        # HTTP server port
IP = "130.229.164.26"  # IP address of the server

connected = set()
ids = {}
next_id = 1

# CORS configuration for WebSocket
ALLOWED_ORIGINS = [
    "https://wizzyworks-frontend.vercel.app",
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

def check_origin(origin):
    """Check if the origin is allowed for WebSocket connections"""
    if not origin:
        return True  # Allow connections without origin header (like from Postman, etc.)
    
    # Allow all localhost and 127.0.0.1 origins for development
    parsed = urlparse(origin)
    if parsed.hostname in ['localhost', '127.0.0.1']:
        return True
        
    return origin in ALLOWED_ORIGINS

async def hostHandler(websocket):
    global next_id
    host, port = websocket.remote_address
    
    connected.add(websocket)
    ids[websocket] = next_id
    client_id = next_id
    next_id += 1

    print(f"Host connected: {host}:{port} -> ID {client_id}")

    try:
        async for message in websocket:
            print(f"Received from ID {client_id}: {message}")
            for ws in connected:
                if ws.open:
                    await ws.send(f"[{client_id}] {message}")
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for ID {client_id}")
    except Exception as e:
        print(f"Error with ID {client_id}: {e}")
    finally:
        connected.remove(websocket)
        ids.pop(websocket, None)
        print(f"Host disconnected: ID {client_id}")


# HTTP server with CORS support
class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def start_http_server():
    os.chdir("web")  # serve files from ./web folder
    handler = CORSHTTPRequestHandler
    with socketserver.TCPServer(("", HTTP_PORT), handler) as httpd:
        print(f"HTTP server running at http://{get_local_ip()}:{HTTP_PORT}")
        httpd.serve_forever()

# Helper: get LAN IP
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()
        
# Main
async def main():
    # Start HTTP server in background thread
    threading.Thread(target=start_http_server, daemon=True).start()

    # Generate QR code for the HTTP site
    url = "https://wizzyworks-frontend.vercel.app/"
    img = qrcode.make(url)
    img.save("./qr_code.png")
    print(f"Scan the QR code (qr_code.png) or open {url}")

    # Start WebSocket server with CORS support
    async with serve(
        hostHandler, 
        HOST, 
        PORT,
        origins=None  # Allow all origins - you can restrict this to ALLOWED_ORIGINS for production
    ):
        print(f"WebSocket server running at ws://{get_local_ip()}:{PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
