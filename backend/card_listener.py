import asyncio
import websockets
import time
from smartcard.System import readers

from card import get_card_uid


WEBSOCKET_PORT = 8765


async def send_card_uid(card_uid):
    uri = f"ws://localhost:{WEBSOCKET_PORT}"
    async with websockets.connect(uri) as websocket:
        await websocket.send(f'{{"type": "open_door", "code": "{card_uid}"}}')
        print(f"Sent open_door for card UID: {card_uid}")


def main():
    print("Starting card listener for opening door...")
    all_readers = readers()
    if not all_readers:
        print("No readers found!")
        return

    device = str(all_readers[0])
    while True:
        card_uid = get_card_uid(device)
        if card_uid:
            try:
                asyncio.run(send_card_uid(card_uid))
            except Exception as e:
                print(f"Error sending card UID: {e}")
            time.sleep(1)
        else:
            time.sleep(0.1)


if __name__ == "__main__":
    main()
