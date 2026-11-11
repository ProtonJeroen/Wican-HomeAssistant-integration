"""WiCAN voltage and battery percentage sensors."""
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.sensor import RestoreSensor
from .entity import WiCANEntity
from .const import POWER_KEYS

PERCENTAGES = ("soc_d", "soc", "soh")
POWER_SENSORS = {
    "hv_voltage": ("HV-accuspanning", "V", SensorDeviceClass.VOLTAGE),
    "battery_current": ("Accustroom", "A", SensorDeviceClass.CURRENT),
    "battery_power": ("Netto accuvermogen", "kW", SensorDeviceClass.POWER),
}

async def async_setup_entry(hass, entry, async_add_entities):
    entities = [WiCANSensor(entry.runtime_data, key, name) for key, name in
                       (("voltage", "12V accuspanning"), ("soc_d", "Accupercentage"),
                        ("soc", "BMS accupercentage"), ("soh", "Accugezondheid"))]
    entities.extend(WiCANSensor(entry.runtime_data, key, POWER_SENSORS[key][0])
                    for key in POWER_KEYS if entry.runtime_data.config.get(f"{key}_topic"))
    async_add_entities(entities)

class WiCANSensor(WiCANEntity, RestoreSensor):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, runtime, key, name):
        super().__init__(runtime, key)
        self._attr_name = name
        self._attr_native_unit_of_measurement = "V" if key == "voltage" else "%"
        self._attr_device_class = SensorDeviceClass.VOLTAGE if key == "voltage" else SensorDeviceClass.BATTERY
        if key in POWER_SENSORS:
            _, unit, device_class = POWER_SENSORS[key]
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = device_class
        self._attr_suggested_display_precision = 2 if key == "battery_power" else 1

    @property
    def native_value(self):
        return self.runtime.state.values.get(self.key)

    @property
    def available(self):
        if self.key not in PERCENTAGES:
            return super().available
        return self.runtime.state.percentage_available(self.key)

    @property
    def extra_state_attributes(self):
        if self.key not in PERCENTAGES:
            return None
        fresh = self.runtime.available(self.key)
        return {
            "last_measured_at": self.runtime.state.measured_at.get(self.key),
            "data_fresh": fresh,
            "value_source": "live" if fresh else "last_known",
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.key not in PERCENTAGES:
            return
        previous_data = await self.async_get_last_sensor_data()
        previous_state = await self.async_get_last_state()
        if previous_data is not None:
            measured_at = (previous_state.attributes.get("last_measured_at")
                           if previous_state is not None else None)
            self.runtime.state.restore_percentage(
                self.key, previous_data.native_value, measured_at)
