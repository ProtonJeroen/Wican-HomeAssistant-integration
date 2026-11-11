"""WiCAN charging state sensors."""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .entity import WiCANEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WiCANBinarySensor(entry.runtime_data, key, name) for key, name in
                       (("charger_connected", "Laadstekker aangesloten"),
                        ("charging", "Laden"), ("charging_dc", "DC laden"))])

class WiCANBinarySensor(WiCANEntity, BinarySensorEntity):
    def __init__(self, runtime, key, name):
        super().__init__(runtime, key)
        self._attr_name = name
        self._attr_device_class = (BinarySensorDeviceClass.PLUG if key == "charger_connected"
                                   else BinarySensorDeviceClass.BATTERY_CHARGING)

    @property
    def is_on(self):
        return self.runtime.state.values.get(self.key)
