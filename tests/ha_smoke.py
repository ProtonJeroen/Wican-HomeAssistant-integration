"""Run separately with Home Assistant installed: python tests/ha_smoke.py."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from custom_components.wican_mqtt.config_flow import schema, validate
from custom_components.wican_mqtt.sensor import WiCANSensor
from custom_components.wican_mqtt.binary_sensor import WiCANBinarySensor
from custom_components.wican_mqtt.runtime import WiCANRuntime
from homeassistant.components import mqtt
from types import SimpleNamespace
assert callable(mqtt.async_wait_for_mqtt_client)
assert callable(mqtt.async_subscribe)
assert callable(mqtt.async_publish)
data=schema({},True)({'device_id':'dcb4d92aa961'})
data=validate(data,data['device_id'])
assert data['status_topic']=='wican-pro/dcb4d92aa961/can/status'
r=WiCANRuntime(None,SimpleNamespace(data=data,options={}))
s=WiCANSensor(r,'voltage','12V accuspanning')
assert s.native_unit_of_measurement=='V'
assert s.device_class=='voltage'
assert s.state_class=='measurement'
assert not s.available
b=WiCANBinarySensor(r,'charging','Laden')
assert b.device_class=='battery_charging'
assert not b.available
for changes in ({'status_topic':data['soc_d_topic']},{'status_topic':'wican/dcb4d92aa961/rsp'},{'stale_after':60}):
 try:validate({**data,**changes},data['device_id'])
 except ValueError:pass
 else:raise AssertionError(changes)
print('HA imports, schema, topic checks, entity metadata: PASS')
