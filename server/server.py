import asyncio
import websockets
from websockets.asyncio.server import serve
import http.server
import socketserver
import threading
import qrcode
import os
import socket


HOST = "0.0.0.0"        # Listen on all interfaces
PORT = 8765             # WebSocket port
HTTP_PORT = 8000        # HTTP server port
IP = "130.229.131.160"  # IP address of the server

connected = set()

# WebSocket handler
async def phoneHandler(websocket):
    connected.add(websocket)
    try:
        async for message in websocket:
            print(f"Received: {message}")
            # Echo to everyone
            for ws in connected:
                if ws.open:
                    await ws.send(f"Echo: {message}")
    finally:
        connected.remove(websocket)

# HTTP server 
def start_http_server():
    os.chdir("web")  # serve files from ./web folder
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", HTTP_PORT), handler) as httpd:
        print(f"HTTP server running at http://{IP}:{HTTP_PORT}")
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
    url = f"http://{IP}:{HTTP_PORT}"
    img = qrcode.make(url)
    img.save("C:\\KTH\\AGI25\\wizzyworks-server\\server\\qr_code.png")
    print(f"Scan the QR code (qr_code.png) or open {url}")

    # Start WebSocket server
    async with serve(phoneHandler, HOST, PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
