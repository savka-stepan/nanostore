import subprocess
import time


def trigger_relay(timeout_ms: int):
    """Trigger relay with timeout using usblrb as a subprocess."""
    subprocess.run(
        ["poetry", "run", "python", "usblrb.py", "-d", "0", "-s", "123"], check=True
    )
    time.sleep(timeout_ms / 1000)
    subprocess.run(
        ["poetry", "run", "python", "usblrb.py", "-d", "0", "-s", "122"], check=True
    )
