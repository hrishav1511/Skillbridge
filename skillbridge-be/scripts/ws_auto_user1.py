#!/usr/bin/env python3
"""Automated quick test: create room, connect as user1, send a message and exit."""

import asyncio
import json
import os
import time

import urllib.request
import urllib.error
import websockets

SERVER = os.environ.get("SB_SERVER", "http://127.0.0.1:8000")
WS_SERVER = SERVER.replace("http://", "ws://")
USER_ID = "fb9f6666-5a45-48ac-8a45-66ed85557baa"
TARGET_USER_UUID = os.environ.get("SB_TARGET_USER_UUID")
ROOM_FILE = os.environ.get(
    "SB_ROOM_FILE", f"/tmp/skillbridge_chat_room_{USER_ID}_<target>.json"
)


def encode(payload: dict) -> str:
    return json.dumps(payload)


def decode(raw: str) -> dict:
    return json.loads(raw)


def create_direct_room(target_uuid: str):
    if not target_uuid:
        print(
            "No TARGET_USER_UUID supplied via SB_TARGET_USER_UUID; cannot create room."
        )
        return None
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
            try:
                with open(ROOM_FILE, "w") as f:
                    json.dump({"chat_room_id": data.get("chat_room_id")}, f)
            except Exception:
                pass
            return data.get("chat_room_id")
    except urllib.error.HTTPError as e:
        print("HTTPError while creating room:", e)
        return None
    except Exception as e:
        print("Error while creating room:", e)
        return None


async def main():
    room_id = None
    # Try to create if TARGET_USER_UUID provided
    if TARGET_USER_UUID:
        room_id = create_direct_room(TARGET_USER_UUID)

    if not room_id:
        print(
            "No chat_room_id available. Please set SB_ROOM_FILE or SB_CHAT_ROOM_ID or provide SB_TARGET_USER_UUID."
        )
        return

    uri = f"{WS_SERVER}/api/v1/chat/ws/{USER_ID}"
    print("Connecting to", uri)

    async with websockets.connect(uri, origin="http://localhost") as ws:
        print("Connected, sending test message...")
        payload = {
            "type": "send_message",
            "payload": {
                "chat_room_id": room_id,
                "content": "Hello from automated user1",
            },
        }
        await ws.send(encode(payload))
        # wait a bit for any server responses
        start = time.time()
        while time.time() - start < 5:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)
                print("RECV:", decode(msg))
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
