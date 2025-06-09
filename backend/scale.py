import usblrb
import time
import serial.tools.list_ports

SCALE_VID = "1A86"
SCALE_PID = "7523"


def trigger_relay(timeout_ms: int):
    """Trigger relay with timeout using usblrb."""
    usblrb.main(["-d", "0", "-s", "123"])
    time.sleep(timeout_ms / 1000)
    usblrb.main(["-d", "0", "-s", "122"])


def get_scale_port() -> str | None:
    """Find the USB scale port by VID and PID."""
    for device in serial.tools.list_ports.comports():
        if device.vid and device.pid:
            vid = f"{device.vid:04X}"
            pid = f"{device.pid:04X}"
            if vid == SCALE_VID and pid == SCALE_PID:
                return device.device
    return None
