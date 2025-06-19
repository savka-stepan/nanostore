from smartcard.System import readers
from smartcard.Exceptions import CardRequestTimeoutException
from smartcard.util import toBytes, toHexString

import asyncio
import time


def get_card_uid(device: str = None) -> str | None:
    """Wait for a smartcard and return its UID from a specific device/reader."""
    all_readers = readers()
    if not all_readers:
        print("No smartcard readers found.")
        return None

    # Select the reader by name if provided, else use the first one
    reader = None
    if device:
        for r in all_readers:
            if device in str(r):
                reader = r
                break
        if not reader:
            print(f"Reader '{device}' not found.")
            return None
    else:
        reader = all_readers[0]

    while True:
        try:
            connection = reader.createConnection()
            connection.connect()
            command = toBytes("FF CA 00 00 00")
            data, sw1, sw2 = connection.transmit(command)
            uid = toHexString(data).replace(" ", "")
            status = f"{sw1:02X} {sw2:02X}"
            if status == "90 00":
                return uid.lower()
            else:
                print(f"Invalid card status: {status}")
        except CardRequestTimeoutException:
            pass
        except Exception as e:
            # If no card is present or another error occurs, just continue
            time.sleep(0.1)


# # Test function to simulate card UID retrieval
# def get_card_uid(device: str = None) -> str | None:
#     # For testing, return a fixed UID string
#     return "e3429c04"


async def get_card_uid_async(device: str = None) -> str | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_card_uid, device)
