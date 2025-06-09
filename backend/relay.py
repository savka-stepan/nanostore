import usblrb
import time


def trigger_relay(timeout_ms: int):
    """Trigger relay with timeout using usblrb."""
    usblrb.main(["-d", "0", "-s", "123"])
    print("Relay triggered for 123")
    time.sleep(timeout_ms / 1000)
    print("Waiting for relay to reset...")
    usblrb.main(["-d", "0", "-s", "122"])
    print("Relay reset to 122")
