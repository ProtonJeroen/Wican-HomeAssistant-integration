"""WiCAN voltage and battery percentage sensors."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from .entity import WiCANEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WiCANSensor(entry.runtime_data, key, name) for key, name in
                       (("voltage", "12V accuspanning"), ("soc_d", "Accupercentage"),
                        ("soc", "BMS accupercentage"), ("soh", "Accugezondheid"))])

class WiCANSensor(WiCANEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, runtime, key, name):
        super().__init__(runtime, key)
        self._attr_name = name
        self._attr_native_unit_of_measurement = "V" if key == "voltage" else "%"
        self._attr_device_class = SensorDeviceClass.VOLTAGE if key == "voltage" else SensorDeviceClass.BATTERY
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self):
        return self.runtime.state.values.get(self.key)
