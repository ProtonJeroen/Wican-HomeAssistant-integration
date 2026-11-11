"""Shared entity behavior."""
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

class WiCANEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, runtime, key):
        self.runtime = runtime
        self.key = key
        self._attr_unique_id = f"{runtime.id}_{key}"
        self._attr_device_info = runtime.device_info

    @property
    def available(self):
        return self.runtime.available(self.key)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.runtime.listeners.add(self.async_write_ha_state)
        self.async_on_remove(lambda: self.runtime.listeners.discard(self.async_write_ha_state))
