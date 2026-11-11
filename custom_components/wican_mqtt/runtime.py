"""MQTT subscriptions, polling and expiry."""
import logging
from datetime import timedelta
from time import monotonic
from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, POWER_KEYS
from .protocol import Values, decode, number, flag

_LOGGER = logging.getLogger(__name__)

class WiCANRuntime:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.config = {**entry.data, **entry.options}
        for key in POWER_KEYS:
            self.config.setdefault(f"{key}_topic", "")
        self.state = Values()
        self.listeners = set()
        self.unsubs = []
        self.stopped = False
        self.next_poll = 0
        self.pending_until = 0
        self.next_probe = 0
        self.timeout = self.config["stale_after"]
        self.id = entry.data["device_id"]
        # Firmware 4.52p hard-codes these independently of the status topic.
        self.command_topic = f"wican/{self.id}/cmd"
        self.response_topic = f"wican/{self.id}/rsp"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.id)},
                "name": self.config["name"], "manufacturer": "MeatPi",
                "model": self.config["model"]}

    def notify(self):
        for listener in tuple(self.listeners):
            listener()

    async def async_start(self):
        topics = {self.response_topic, self.config["status_topic"]}
        topics.update(self.config[f"{key}_topic"] for key in
                      ("soc_d", "soc", "soh", "charger_connected", "charging", "charging_dc"))
        topics.update(self.config[f"{key}_topic"] for key in POWER_KEYS
                      if self.config[f"{key}_topic"])
        for topic in topics:
            self.unsubs.append(await mqtt.async_subscribe(self.hass, topic, self.message, 0))
        self.unsubs.append(async_track_time_interval(
            self.hass, self.tick, timedelta(seconds=5)))
        # First poll follows subscription registration, on the first timer tick.

    @callback
    def message(self, message):
        if self.stopped:
            return
        data = decode(message.payload)
        now = monotonic()
        if message.topic == self.config["status_topic"]:
            status = data.get("status")
            if status == "offline" and not message.retain:
                self.state.offline = True
                self.state.received.clear()
                self.pending_until = 0
                self.next_probe = now + 300
            elif status == "online":
                # Retained online is a hint to probe, not proof of availability.
                self.next_poll = 0
                self.next_probe = 0
            self.notify()
            return
        if message.retain:
            return
        if message.topic == self.response_topic:
            # Only accept a fresh reply in the window after our own request.
            if now <= self.pending_until and self.pending_until:
                value = number(data.get("battery_voltage"), 0, 30)
                if self.state.update("voltage", value, now):
                    self.pending_until = 0
        else:
            for key, field in (("soc_d", "SOC_D"), ("soc", "SOC"), ("soh", "SOH"),
                               ("charger_connected", "CHARGER_CONNECTED"),
                               ("charging", "CHARGING"), ("charging_dc", "CHARGING_DC"),
                               ("hv_voltage", "HV_VOLTAGE"),
                               ("battery_current", "BATTERY_CURRENT"),
                               ("battery_power", "BATTERY_POWER")):
                if message.topic != self.config[f"{key}_topic"]:
                    continue
                value = data.get(field)
                limits = {"soc_d": (0, 100), "soc": (0, 100), "soh": (0, 100),
                          "hv_voltage": (0, 500), "battery_current": (-1000, 1000),
                          "battery_power": (-500, 500)}
                parsed = number(value, *limits[key]) if key in limits else flag(value)
                self.state.update(key, parsed, now)
        self.notify()

    async def tick(self, _now):
        if self.stopped:
            return
        self.notify()  # Expire each sensor even when no messages arrive.
        now = monotonic()
        fresh = any(self.state.available(k, now, self.timeout) for k in self.state.received)
        if now < self.next_poll or (not fresh and now < self.next_probe):
            return
        # Non-retained probes are harmless while asleep; no queued wake-up commands.
        # Without fresh traffic probe at most once per five minutes.
        self.next_poll = now + self.config["poll_interval"]
        self.next_probe = now + 300
        self.pending_until = now + 15
        try:
            await mqtt.async_publish(self.hass, self.command_topic,
                                     '{"cmd":"get_vbatt"}', qos=0, retain=False)
        except Exception:
            self.pending_until = 0
            _LOGGER.warning("Could not request WiCAN voltage", exc_info=True)

    def available(self, key):
        return self.state.available(key, monotonic(), self.timeout)

    def stop(self):
        self.stopped = True
        for unsub in self.unsubs:
            unsub()
        self.unsubs.clear()
        self.listeners.clear()
