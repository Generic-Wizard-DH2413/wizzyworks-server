import asyncio
import websockets
import websockets.exceptions
from websockets.asyncio.server import serve
import os
import socket
from urllib.parse import urlparse
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

HOST = os.getenv("HOST", "0.0.0.0")        # Listen on all interfaces
PORT = int(os.getenv("WS_PORT", "8765"))             # WebSocket port
HTTP_PORT = int(os.getenv("HEALTH_PORT", "8000"))    # Health check port

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
    "http://127.0.0.1:8000",
    "http://192.168.3.7:5173",
    "http://192.168.3.7:5173"
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
            # Try to parse the message as JSON
            try:
                data = json.loads(message)
            except Exception:
                print("Bridge sent non-JSON message, ignoring.")
                continue

            # Find the websocket with matching ID
            target_id = data.get("id")
            if target_id is not None:
                for ws, cid in ids.items():
                    if cid == target_id:
                        await ws.send(message)
                        print(f"Message to the frontend: {message}")
                        print(f"Forwarded bridge message to client id {target_id}")
                        break
                else:
                    print(f"No connected client with id {target_id} to forward bridge message.")
            else:
                print("Bridge message missing 'id' field, not forwarded.")
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
        # Add timeout to prevent hanging on incomplete connections
        first_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
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
        
    except asyncio.TimeoutError:
        print(f"Timeout waiting for first message from {host}:{port}")
        await websocket.close()
        return
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed during handshake from {host}:{port}")
        return
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in first message from {host}:{port}: {e}")
        await websocket.close()
        return
    except Exception as e:
        print(f"Error during handshake from {host}:{port}: {e}")
        return

    # If valid -> proceed as before (only for regular clients)

    # Check if websocket is already connected to prevent duplicate ID assignment
    if websocket not in connected:
        connected.add(websocket)
        # Assign the smallest available ID if possible, else use next_id
        if available_ids:
            client_id = min(available_ids)
            available_ids.remove(client_id)
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
                    try:
                        await bridge.send(json.dumps(data))
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

# Minimal health check server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health_status = {
                "status": "healthy",
                "websocket_port": PORT,
                "connected_clients": len(connected),
                "bridge_connected": bridge is not None
            }
            self.wfile.write(json.dumps(health_status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass

def start_health_server():
    httpd = HTTPServer(("0.0.0.0", HTTP_PORT), HealthCheckHandler)
    print(f"Health check server running at http://{get_local_ip()}:{HTTP_PORT}/health")
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
    # Start minimal health check server in background thread
    threading.Thread(target=start_health_server, daemon=True).start()

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
