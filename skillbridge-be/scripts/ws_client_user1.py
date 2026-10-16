#!/usr/bin/env python3
"""Interactive websocket client for user 1.

Creates (or reads) a direct chat room with target user 2, connects to the
server WS endpoint and lets you type messages to send to that room. Incoming
messages are printed to the terminal.
"""

import asyncio
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import urllib.request
import urllib.error
import websockets

SERVER = os.environ.get("SB_SERVER", "http://127.0.0.1:8000")
WS_SERVER = SERVER.replace("http://", "ws://")
USER_ID = int(os.environ.get("SB_USER_ID", "1"))
TARGET_USER_UUID = os.environ.get("SB_TARGET_USER_UUID")
ROOM_FILE = os.environ.get(
    "SB_ROOM_FILE", f"/tmp/skillbridge_chat_room_{USER_ID}_<target>.json"
)


def encode(payload: dict) -> str:
    return json.dumps(payload)


def decode(raw: str) -> dict:
    return json.loads(raw)


def create_direct_room(target_uuid: str):
    url = f"{SERVER}/api/v1/chat/rooms/direct"
    req = urllib.request.Request(
        url,
        data=json.dumps({"target_user_id": target_uuid}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            data = json.loads(body)
            return data.get("chat_room_id")
    except urllib.error.HTTPError as e:
        print("Failed to create direct room HTTPError:", e)
        return None
    except Exception as e:
        print("Failed to create direct room:", e)
        return None


async def stdin_reader(loop):
    with ThreadPoolExecutor(1) as pool:
        while True:
            line = await loop.run_in_executor(pool, sys.stdin.readline)
            if not line:
                return
            yield line.rstrip("\n")


async def main():
    # create or read room id
    room_id = None
    if os.path.exists(ROOM_FILE):
        try:
            with open(ROOM_FILE, "r") as f:
                room_id = json.load(f).get("chat_room_id")
        except Exception:
            room_id = None

    # If a target user UUID is provided via env, try to create the direct room
    if not room_id and TARGET_USER_UUID:
        print("Creating direct room (via TARGET_USER_UUID)...")
        room_id = create_direct_room(TARGET_USER_UUID)
        if room_id:
            try:
                with open(ROOM_FILE, "w") as f:
                    json.dump({"chat_room_id": room_id}, f)
            except Exception:
                pass

    if not room_id:
        print(
            "Cannot determine chat_room_id. Set SB_ROOM_FILE or SB_TARGET_USER_UUID, or supply a chat_room_id manually."
        )
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
