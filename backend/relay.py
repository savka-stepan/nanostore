import subprocess
import time


def trigger_relay(timeout_ms: int):
    """Trigger relay with timeout using usblrb as a subprocess."""
    subprocess.run(
        ["poetry", "run", "python", "usblrb.py", "-d", "0", "-s", "123"], check=True
    )
    print("Relay triggered for 123")
    time.sleep(timeout_ms / 1000)
    print("Waiting for relay to reset...")
    subprocess.run(
        ["poetry", "run", "python", "usblrb.py", "-d", "0", "-s", "122"], check=True
    )
    print("Relay reset to 122")
