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
data=schema({},True)({'device_id':'aabb11223344'})
data=validate(data,data['device_id'])
assert data['status_topic']=='wican-pro/aabb11223344/can/status'
r=WiCANRuntime(None,SimpleNamespace(data=data,options={}))
s=WiCANSensor(r,'voltage','12V accuspanning')
assert s.native_unit_of_measurement=='V'
assert s.device_class=='voltage'
assert s.state_class=='measurement'
assert not s.available
b=WiCANBinarySensor(r,'charging','Laden')
assert b.device_class=='battery_charging'
assert not b.available
for changes in ({'status_topic':data['soc_d_topic']},{'status_topic':'wican/aabb11223344/rsp'},{'stale_after':60}):
 try:validate({**data,**changes},data['device_id'])
 except ValueError:pass
 else:raise AssertionError(changes)
print('HA imports, schema, topic checks, entity metadata: PASS')
soc=WiCANSensor(r,'soc_d','Accupercentage')
r.state.restore_percentage('soc_d',25,'2026-11-11T19:26:04+00:00')
assert soc.available and soc.native_value==25
assert soc.extra_state_attributes['data_fresh'] is False
assert soc.extra_state_attributes['last_measured_at']=='2026-11-11T19:26:04+00:00'
r.state.update('soc_d',26, __import__('time').monotonic())
assert soc.extra_state_attributes['data_fresh'] is True
r.state.offline=True
assert soc.available and soc.extra_state_attributes['data_fresh'] is False
assert not s.available and not b.available
print('HA sensor last-known/fresh/offline behavior: PASS')
for key,unit,device_class in [('hv_voltage','V','voltage'),('battery_current','A','current'),('battery_power','kW','power')]:
 sensor=WiCANSensor(r,key,key)
 assert sensor.native_unit_of_measurement==unit and sensor.device_class==device_class
 assert not sensor.available and sensor.extra_state_attributes is None
for changes in ({'battery_power_topic':data['soc_d_topic']},{'hv_voltage_topic':'a/#'},{'battery_current_topic':'wican/aabb11223344/cmd'}):
 try:validate({**data,**changes},data['device_id'])
 except ValueError:pass
 else:raise AssertionError(changes)
assert validate(data,data['device_id'])['battery_power_topic']==''
print('HA optional HV topics, signed power metadata and validation: PASS')

from custom_components.wican_mqtt.binary_sensor import WiCANReachableSensor
reach=WiCANReachableSensor(r)
assert reach.device_class=='connectivity' and not reach.available
r.contact_at=__import__('time').monotonic(); r.connection_offline=False
assert reach.available and reach.is_on
r.connection_offline=True
assert reach.available and not reach.is_on
assert reach.extra_state_attributes['sleep_confirmed'] is False
print('HA reachability sensor remains visible while offline: PASS')
