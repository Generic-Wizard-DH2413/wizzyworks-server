import asyncio
import websockets
import json

async def test_websocket():
    uri = "wss://wizzyworks-server.redbush-85e59e10.swedencentral.azurecontainerapps.io"
    
    try:
        print(f"Attempting to connect to: {uri}")
        print("Connecting...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established!")
            
            # Send connection message
            connection_msg = {"type": "connection"}
            await websocket.send(json.dumps(connection_msg))
            print(f"📤 Sent: {connection_msg}")
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Parse response
            try:
                data = json.loads(response)
                if data.get("code") == 0:
                    client_id = data.get("data", {}).get("id")
                    print(f"🎉 Successfully connected with ID: {client_id}")
                else:
                    print(f"⚠️ Unexpected response: {data}")
            except json.JSONDecodeError:
                print(f"⚠️ Non-JSON response: {response}")
            
    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection was closed by the server")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e.status_code}")
    except websockets.exceptions.InvalidURI:
        print("❌ Invalid WebSocket URI")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())