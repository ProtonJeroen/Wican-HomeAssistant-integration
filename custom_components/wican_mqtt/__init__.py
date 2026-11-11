"""Local MQTT integration for WiCAN and WiCAN Pro."""
from homeassistant.components import mqtt
from homeassistant.exceptions import ConfigEntryNotReady
from .const import PLATFORMS
from .runtime import WiCANRuntime

async def async_setup_entry(hass, entry):
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("MQTT client is not ready")
    runtime = WiCANRuntime(hass, entry)
    entry.runtime_data = runtime
    try:
        await runtime.async_start()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        runtime.stop()
        raise
    entry.async_on_unload(entry.add_update_listener(async_reload))
    return True

async def async_reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry.runtime_data.stop()
        return True
    return False
