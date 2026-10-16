#!/usr/bin/env python3
"""Interactive websocket client for user 2.

Waits for the room file written by user1 (in /tmp) and connects to the same
chat room. Type messages to send.
"""

import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import websockets

SERVER = os.environ.get("SB_SERVER", "http://127.0.0.1:8000")
WS_SERVER = SERVER.replace("http://", "ws://")
USER_ID = int(os.environ.get("SB_USER_ID", "2"))
ROOM_FILE = os.environ.get(
    "SB_ROOM_FILE", f"/tmp/skillbridge_chat_room_1_{USER_ID}.json"
)
CHAT_ROOM_ID = os.environ.get("SB_CHAT_ROOM_ID")


def encode(payload: dict) -> str:
    return json.dumps(payload)


def decode(raw: str) -> dict:
    return json.loads(raw)


async def stdin_reader(loop):
    with ThreadPoolExecutor(1) as pool:
        while True:
            line = await loop.run_in_executor(pool, sys.stdin.readline)
            if not line:
                return
            yield line.rstrip("\n")


async def main():
    # wait for room id
    room_id = CHAT_ROOM_ID
    if not room_id:
        print("Waiting for room file:", ROOM_FILE)
        for _ in range(60):
            if os.path.exists(ROOM_FILE):
                try:
                    with open(ROOM_FILE, "r") as f:
                        room_id = json.load(f).get("chat_room_id")
                    break
                except Exception:
                    pass
            await asyncio.sleep(1)

    if not room_id:
        print("Room file not found and SB_CHAT_ROOM_ID not set. Exiting.")
        return

    uri = f"{WS_SERVER}/api/v1/chat/ws/{USER_ID}"
    print("Connecting to", uri)

    async with websockets.connect(uri, origin="http://localhost") as ws:
        print("Connected. Type messages and press Enter to send. Ctrl-D to quit.")

        async def receiver():
            try:
                async for msg in ws:
                    try:
                        frame = decode(msg)
                    except Exception:
                        print("<- raw:", msg)
                        continue
                    print("<-", frame)
            except websockets.ConnectionClosed:
                print("Connection closed")

        async def sender():
            loop = asyncio.get_running_loop()
            async for line in stdin_reader(loop):
                payload = {
                    "type": "send_message",
                    "payload": {"chat_room_id": room_id, "content": line},
                }
                await ws.send(encode(payload))

        await asyncio.gather(receiver(), sender())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting")
