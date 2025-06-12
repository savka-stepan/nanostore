import asyncio
import websockets
import time

from card import get_card_uid


WEBSOCKET_PORT = 8765


async def send_card_uid(card_uid):
    uri = "ws://localhost:{WEBSOCKET_PORT}/"
    async with websockets.connect(uri) as websocket:
        await websocket.send(f'{{"type": "open_door", "code": "{card_uid}"}}')
        print(f"Sent open_door for card UID: {card_uid}")


def main():
    print("Starting card listener...")
    while True:
        # TODO: For production, get device from database or config
        device = "ACS ACR122U 00 00"
        card_uid = get_card_uid(device)
        if card_uid:
            asyncio.run(send_card_uid(card_uid))
        else:
            time.sleep(0.1)


if __name__ == "__main__":
    main()
