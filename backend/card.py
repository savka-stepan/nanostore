from smartcard.CardRequest import CardRequest
from smartcard.CardType import AnyCardType
from smartcard.Exceptions import CardRequestTimeoutException
from smartcard import util


def get_card_uid() -> str | None:
    """Wait for a smartcard and return its UID."""
    card_type = AnyCardType()
    request = CardRequest(timeout=0, cardType=card_type)

    while True:
        try:
            service = request.waitforcard()
            conn = service.connection
            conn.connect()

            command = util.toBytes("FF CA 00 00 00")
            data, sw1, sw2 = conn.transmit(command)

            uid = util.toHexString(data).replace(" ", "")
            status = f"{sw1:02X} {sw2:02X}"

            if status == "90 00":
                return uid.lower()
            else:
                print(f"Invalid card status: {status}")
        except CardRequestTimeoutException:
            pass


# # Test function to simulate card UID retrieval
# def get_card_uid():
#     # For testing, return a fixed UID string
#     return "e3429c04"
