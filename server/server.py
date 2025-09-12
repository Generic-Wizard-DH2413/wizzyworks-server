import asyncio
import websockets
from websockets.asyncio.server import serve
import http.server
import socketserver
import threading
import qrcode
import os
import socket
import PIL

HOST = "0.0.0.0"        # Listen on all interfaces
PORT = 8765             # WebSocket port
HTTP_PORT = 8000        # HTTP server port
IP = "130.229.131.160"  # IP address of the server

connected = set()
ids = {}
next_id = 1

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
    finally:
        connected.remove(websocket)
        ids.pop(websocket, None)
        print(f"Host disconnected: ID {client_id}")


# HTTP server 
def start_http_server():
    os.chdir("web")  # serve files from ./web folder
    handler = http.server.SimpleHTTPRequestHandler
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
    img.save("C:\\KTH\\AGI25\\wizzyworks-server\\server\\qr_code.png")
    print(f"Scan the QR code (qr_code.png) or open {url}")

    # Start WebSocket server
    async with serve(hostHandler, HOST, PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
