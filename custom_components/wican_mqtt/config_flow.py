"""UI setup and editable MQTT settings."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
from .protocol import device_id, topic

KEYS = ("soc_d", "soc", "soh", "charger_connected", "charging", "charging_dc")

def schema(values, initial=False):
    fields = {}
    if initial:
        fields[vol.Required("device_id")] = str
    fields[vol.Required("name", default=values.get("name", "WiCAN Pro"))] = str
    fields[vol.Required("model", default=values.get("model", "WiCAN Pro"))] = vol.In(["WiCAN", "WiCAN Pro"])
    fields[vol.Required("status_topic", default=values.get("status_topic", "wican-pro/DEVICE_ID/can/status"))] = str
    for key in KEYS:
        fields[vol.Required(f"{key}_topic", default=values.get(f"{key}_topic", f"wican-pro/ioniq/{key}"))] = str
    fields[vol.Required("poll_interval", default=values.get("poll_interval", 60))] = vol.All(vol.Coerce(int), vol.Range(min=30, max=3600))
    fields[vol.Required("stale_after", default=values.get("stale_after", 180))] = vol.All(vol.Coerce(int), vol.Range(min=60, max=7200))
    return vol.Schema(fields)

def validate(data, identity):
    result = dict(data)
    result["name"] = result["name"].strip()
    if not result["name"]:
        raise ValueError("invalid_name")
    for key in ("status_topic", *(f"{key}_topic" for key in KEYS)):
        result[key] = topic(result[key].replace("DEVICE_ID", identity))
    all_topics = [result["status_topic"], *(result[f"{key}_topic"] for key in KEYS)]
    reserved = {f"wican/{identity}/{suffix}" for suffix in ("cmd", "rsp", "battery")}
    if len(set(all_topics)) != len(all_topics) or reserved.intersection(all_topics):
        raise ValueError("duplicate_topic")
    if result["stale_after"] < result["poll_interval"] * 2:
        raise ValueError("invalid_timeout")
    return result

class WiCANConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                identity = device_id(user_input["device_id"])
                result = validate(user_input, identity)
            except ValueError as err:
                errors["base"] = str(err)
            else:
                await self.async_set_unique_id(identity)
                self._abort_if_unique_id_configured()
                result["device_id"] = identity
                return self.async_create_entry(title=result["name"], data=result)
        return self.async_show_form(step_id="user", data_schema=schema(user_input or {}, True), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WiCANOptionsFlow()

class WiCANOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                result = validate(user_input, self.config_entry.data["device_id"])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                return self.async_create_entry(title="", data=result)
        values = {**self.config_entry.data, **self.config_entry.options, **(user_input or {})}
        return self.async_show_form(step_id="init", data_schema=schema(values), errors=errors)
