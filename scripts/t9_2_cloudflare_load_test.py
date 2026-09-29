"""Measure local room WebSocket throughput at 5, 10, 20 and 30 clients."""
from __future__ import annotations
import asyncio, json, os, time, urllib.request
import websockets
BASE = os.environ.get('GAME_ROOM_URL', 'http://127.0.0.1:8793')
async def one(index: int, seconds: float = 3.0):
    req = urllib.request.Request(f'{BASE}/api/rooms', method='POST')
    with urllib.request.urlopen(req, timeout=60) as response: code = json.load(response)['room_code']
    ws = await websockets.connect(BASE.replace('http', 'ws') + f'/room/{code}')
    sent = received = 0
    try:
        await ws.recv(); await ws.send(json.dumps({'type':'HELLO','version':2})); sent += 1
        await ws.send(json.dumps({'type':'JOIN_ROOM','version':2,'room_code':code,'name':f'load-{index}','created':True})); sent += 1
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            await ws.send(json.dumps({'type':'PING','version':2})); sent += 1
            try: await asyncio.wait_for(ws.recv(), .2); received += 1
            except asyncio.TimeoutError: pass
        return sent, received
    finally: await ws.close()
async def main():
    for users in (5, 10, 20, 30):
        started = time.perf_counter(); rows = await asyncio.gather(*(one(i) for i in range(users)))
        elapsed = time.perf_counter() - started; total = sum(sum(row) for row in rows)
        print(json.dumps({'users':users,'elapsed_s':round(elapsed,2),'messages':total,'messages_per_second':round(total/elapsed,2)}))
if __name__ == '__main__': asyncio.run(main())
