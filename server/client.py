import asyncio, websockets

async def run():
    uri = "http://130.229.131.160:8765"
    async with websockets.connect(uri) as ws:
        await ws.send("MyPhone")
        await ws.send("Hello Server!")
        async for msg in ws:
            print("Server:", msg)

asyncio.run(run())
