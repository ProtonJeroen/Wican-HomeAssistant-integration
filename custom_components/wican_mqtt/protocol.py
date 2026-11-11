"""Pure MQTT decoding and freshness rules."""
import json
import math
import re

def device_id(value):
    value = value.lower().replace(":", "").replace("-", "")
    if not re.fullmatch(r"[0-9a-f]{12}", value):
        raise ValueError("invalid_device_id")
    return value

def topic(value):
    value = value.strip()
    if not value or any(x in value for x in ("#", "+", "\x00")):
        raise ValueError("invalid_topic")
    return value

def decode(payload):
    try:
        data = json.loads(payload)
    except (ValueError, TypeError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}

def number(value, low, high):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and low <= result <= high else None

def flag(value):
    if isinstance(value, bool):
        return value
    if value in (0, "0", "false", "False", "off"):
        return False
    if value in (1, "1", "true", "True", "on"):
        return True
    return None

class Values:
    """Retained readings never become fresh. Freshness is per measurement."""
    def __init__(self):
        self.values = {}
        self.received = {}
        self.offline = False

    def update(self, key, value, now, retained=False):
        if value is None or retained:
            return False
        self.values[key] = value
        self.received[key] = now
        self.offline = False
        return True

    def available(self, key, now, timeout):
        return (not self.offline and key in self.received
                and now - self.received[key] < timeout)
