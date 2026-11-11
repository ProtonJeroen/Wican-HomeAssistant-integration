import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
p=types.ModuleType('subject');p.__path__=[str(Path(__file__).resolve().parents[1]/'custom_components/wican_mqtt')];sys.modules['subject']=p
for n in ('homeassistant','homeassistant.components','homeassistant.components.mqtt','homeassistant.core','homeassistant.helpers','homeassistant.helpers.event'):
 sys.modules[n]=types.ModuleType(n)
sys.modules['homeassistant.core'].callback=lambda f:f
sys.modules['homeassistant.helpers.event'].async_track_time_interval=lambda *args:lambda:None
m=sys.modules['homeassistant.components.mqtt']
p=importlib.import_module('subject.protocol');rt=importlib.import_module('subject.runtime')
class Parsing(unittest.TestCase):
 def test_invalid_voltage(self):
  for v in (True,'nan','inf',-1,31,None,{}):self.assertIsNone(p.number(v,0,30))
  self.assertEqual(p.number('14.8',0,30),14.8)
 def test_bad_json(self):
  for v in ('x','[]','null','1',b'\xff'):self.assertEqual(p.decode(v),{})
 def test_ids_topics(self):
  self.assertEqual(p.device_id('DC:B4:D9:2A:A9:61'),'dcb4d92aa961')
  for v in ('','#','a/+','a\x00b'):
   with self.assertRaises(ValueError):p.topic(v)
 def test_retained_and_expiry(self):
  s=p.Values();s.update('voltage',12.3,1,True);self.assertFalse(s.available('voltage',2,180))
  s.update('voltage',14.8,10);s.update('soc',52,180)
  self.assertFalse(s.available('voltage',191,180));self.assertTrue(s.available('soc',191,180))
 def test_flags(self):
  self.assertFalse(p.flag('0'));self.assertTrue(p.flag('1'));self.assertIsNone(p.flag('unknown'))
class Runtime(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.now=1000;self.patcher=patch.object(rt,'monotonic',lambda:self.now);self.patcher.start();self.addCleanup(self.patcher.stop)
  self.removed=[];self.topics=[]
  async def sub(h,t,cb,q):
   self.topics.append(t);return lambda:self.removed.append(t)
  m.async_subscribe=sub;m.async_publish=AsyncMock()
  self.data={'device_id':'dcb4d92aa961','name':'WiCAN Pro','model':'WiCAN Pro','status_topic':'wicanpro/id/can/status','poll_interval':60,'stale_after':180}
  self.data.update({k+'_topic':'wicanpro/ioniq/'+k for k in ('soc_d','soc','soh','charging','charging_dc','charger_connected')})
  self.r=rt.WiCANRuntime(object(),types.SimpleNamespace(data=self.data,options={}))
  await self.r.async_start()
 def msg(self,t,data,ret=False):self.r.message(types.SimpleNamespace(topic=t,payload=json.dumps(data),retain=ret))
 async def test_live_voltage_and_interval(self):
  await self.r.tick(None)
  c=m.async_publish.call_args;self.assertEqual(c.args[1],'wican/dcb4d92aa961/cmd');self.assertFalse(c.kwargs['retain'])
  self.msg(self.r.response_topic,{'battery_voltage':14.8});self.assertTrue(self.r.available('voltage'))
  self.now+=60;await self.r.tick(None);self.assertEqual(m.async_publish.await_count,2)
 async def test_retained_unsolicited_expired(self):
  self.msg(self.r.response_topic,{'battery_voltage':12.3});self.assertFalse(self.r.available('voltage'))
  await self.r.tick(None);self.msg(self.r.response_topic,{'battery_voltage':12.3},True);self.assertFalse(self.r.available('voltage'))
  self.now+=16;self.msg(self.r.response_topic,{'battery_voltage':14.8});self.assertFalse(self.r.available('voltage'))
 async def test_offline_and_online(self):
  self.msg(self.data['soc_d_topic'],{'SOC_D':52})
  self.msg(self.data['status_topic'],{'status':'offline'},True);self.assertTrue(self.r.available('soc_d'))
  self.msg(self.data['status_topic'],{'status':'offline'});self.assertFalse(self.r.available('soc_d'))
  self.msg(self.data['status_topic'],{'status':'online'},True);self.assertFalse(self.r.available('soc_d'))
  await self.r.tick(None);self.msg(self.r.response_topic,{'battery_voltage':14.8});self.assertTrue(self.r.available('voltage'));self.assertFalse(self.r.available('soc_d'))
 async def test_backoff_and_per_sensor_expiry(self):
  await self.r.tick(None);self.now+=60;await self.r.tick(None);self.assertEqual(m.async_publish.await_count,1)
  self.now+=240;await self.r.tick(None);self.assertEqual(m.async_publish.await_count,2)
  self.msg(self.r.response_topic,{'battery_voltage':14.8});self.now+=181
  self.msg(self.data['soc_d_topic'],{'SOC_D':53});self.assertFalse(self.r.available('voltage'));self.assertTrue(self.r.available('soc_d'))
 async def test_device_isolation_and_cleanup(self):
  other=rt.WiCANRuntime(object(),types.SimpleNamespace(data={**self.data,'device_id':'aabbccddeeff'},options={}))
  self.assertNotEqual(other.device_info['identifiers'],self.r.device_info['identifiers'])
  await self.r.tick(None);self.msg(other.response_topic,{'battery_voltage':10});self.assertFalse(self.r.available('voltage'))
  self.r.stop();self.assertEqual(len(self.removed),len(self.topics));await self.r.tick(None);self.assertEqual(m.async_publish.await_count,1)
