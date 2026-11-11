"""WiCAN charging state sensors."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .entity import WiCANEntity

async def async_setup_entry(hass, entry, async_add_entities):
    entities = [WiCANBinarySensor(entry.runtime_data, key, name) for key, name in
                       (("charger_connected", "Laadstekker aangesloten"),
                        ("charging", "Laden"), ("charging_dc", "DC laden"))]
    entities.append(WiCANReachableSensor(entry.runtime_data))
    async_add_entities(entities)

class WiCANBinarySensor(WiCANEntity, BinarySensorEntity):
    def __init__(self, runtime, key, name):
        super().__init__(runtime, key)
        self._attr_name = name
        self._attr_device_class = (BinarySensorDeviceClass.PLUG if key == "charger_connected"
                                   else BinarySensorDeviceClass.BATTERY_CHARGING)

    @property
    def is_on(self):
        return self.runtime.state.values.get(self.key)


class WiCANReachableSensor(WiCANEntity, BinarySensorEntity):
    """Observed connectivity, never a claim of confirmed sleep."""
    _attr_name = "Bereikbaar"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = "diagnostic"

    def __init__(self, runtime):
        super().__init__(runtime, "reachable")

    @property
    def available(self):
        # Keep the OFF state visible when the other measurements expire.
        return self.runtime.reachable is not None

    @property
    def is_on(self):
        return self.runtime.reachable

    @property
    def extra_state_attributes(self):
        if self.runtime.connection_offline:
            reason = "mqtt_offline"
        elif self.runtime.contact_at is None:
            reason = "no_live_contact"
        elif self.runtime.reachable:
            reason = "live_contact"
        else:
            reason = "contact_timeout"
        return {"connection_reason": reason, "sleep_confirmed": False}
