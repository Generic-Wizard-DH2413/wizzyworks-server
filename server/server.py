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
import json

HOST = "0.0.0.0"        # Listen on all interfaces
PORT = 8765             # WebSocket port
HTTP_PORT = 8000        # HTTP server port
IP = "192.168.0.16"  # IP address of the server

connected = set()
bridge = None
ids = {}
next_id = 1

# Set of reusable IDs
available_ids = set()

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

async def validate_client_message(data, client_id):
    """
    Validate client messages before forwarding to bridge
    TODO: Add actual validation logic here
    """
    # Placeholder for validation logic
    # For now, accept all messages
    print(f"Validating message from client {client_id}")
    
    # Future validation could include:
    # - Message format validation
    # - Rate limiting
    # - Authentication checks
    # - Content filtering
    
    return True  # Accept all messages for now

async def handle_bridge_connection(websocket):
    """Handle bridge connection separately - no ID allocation, no automatic messages"""
    try:
        async for message in websocket:
            print(f"Received from bridge: {message}")
            # Bridge messages are handled here if needed
            # For now, just log them without forwarding to other clients
            
    except websockets.exceptions.ConnectionClosed:
        print("Bridge connection closed")
    except Exception as e:
        print(f"Error with bridge connection: {e}")
    finally:
        global bridge
        bridge = None
        print("Bridge disconnected")

async def hostHandler(websocket):
    global next_id
    host, port = websocket.remote_address

    # First message decides if we keep this client
    try:
        first_message = await websocket.recv()
        print(f"First message from {host}:{port} -> {first_message}")

        data = json.loads(first_message)
        if data.get("type") == "bridge":
            global bridge
            bridge = websocket
            print("Bridge connected")
            # Handle bridge connection separately - no ID allocation, no automatic messages
            await handle_bridge_connection(websocket)
            return
        elif data.get("type") != "connection":
            print("Ignoring non-client connection")
            await websocket.close()
            return
        
    except Exception as e:
        print(f"Error during handshake: {e}")
        return

    # If valid -> proceed as before (only for regular clients)

    # Check if websocket is already connected to prevent duplicate ID assignment
    if websocket not in connected:
        connected.add(websocket)
        # Assign ID from available_ids if possible, else use next_id
        if available_ids:
            client_id = available_ids.pop()
        else:
            client_id = next_id
            next_id += 1
        ids[websocket] = client_id

        print(f"Host connected: {host}:{port} -> id {client_id}")
        package = {"code": 0, "data": {"id": client_id}}
        await websocket.send(json.dumps(package))
    else:
        client_id = ids[websocket]
        print(f"Host already connected: {host}:{port} -> existing id {client_id}")

    try:
        async for message in websocket:
            print(f"Received from id {client_id}: {message}")
            
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"Received invalid JSON from id {client_id}")
                continue
                
            # Validate message (placeholder for future validation logic)
            if await validate_client_message(data, client_id):
                # Forward validated message to bridge if connected
                if bridge:
                    bridge_message = {
                        "aruco_id": client_id,
                        "timestamp": None,  # Add timestamp if needed
                        "data": data
                    }
                    try:
                        await bridge.send(json.dumps(bridge_message))
                        print(f"Forwarded message from client {client_id} to bridge")
                    except websockets.exceptions.ConnectionClosed:
                        print("Bridge connection lost while forwarding message")
                        bridge = None
                    except Exception as e:
                        print(f"Error forwarding to bridge: {e}")
                else:
                    print(f"No bridge connected to forward message from client {client_id}")
            
            # Handle specific message types
            msg_type = data.get("type", "unknown")
            payload = data.get("data", {})

            if msg_type == "response":
                value = payload.get("value", "default fallback")
                print(f"Client {client_id} responded with: {value}")

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for id {client_id}")
    except Exception as e:
        print(f"Error with id {client_id}: {e}")
    finally:
        connected.remove(websocket)
        # Return the ID to available_ids for reuse
        released_id = ids.pop(websocket, None)
        if released_id is not None:
            available_ids.add(released_id)
        print(f"Host disconnected: id {client_id}")

    

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
    url = "http://130.229.179.210:4173/"
    img = qrcode.make(url)
    img.save(os.path.join(os.path.dirname(__file__), "qr_code.png"))
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
