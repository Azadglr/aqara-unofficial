from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from .entity_base import AqaraCoordinatorEntity
from .localize import name as lname
from .resource_definitions import DEVICE_RESOURCE_MAP,CAMERA_TRAIT_MODEL,CAMERA_TRAIT_SWITCHES
async def async_setup_entry(hass,entry,async_add_entities):
    mgr=hass.data[DOMAIN]["aqara_manager"]; ents=[]
    for dev in mgr.get_devices_for_entry(entry.entry_id):
        for item in DEVICE_RESOURCE_MAP.get(dev.model,{}).get("switches",[]): ents.append(AqaraResourceSwitch(hass,dev,item))
        if dev.model==CAMERA_TRAIT_MODEL:
            for item in CAMERA_TRAIT_SWITCHES: ents.append(AqaraTraitSwitch(hass,dev,item))
    async_add_entities(ents)
class AqaraResourceSwitch(AqaraCoordinatorEntity,SwitchEntity):
    def __init__(self,hass,dev,item): super().__init__(hass,dev,item["key"]); self.item=item; self.rid=item["rid"]; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.switch_{dev.did}_{item['key']}"
    @property
    def is_on(self): return str(self.resource_value(self.rid))=="1"
    async def async_turn_on(self,**kwargs):
        await self.manager.session.async_write_resource_device(self.device.did,self.rid,"1"); self.coordinator.data.setdefault("resources",{}).setdefault(self.device.did,{})[self.rid]="1"; self.async_write_ha_state(); await self.coordinator.async_request_refresh()
    async def async_turn_off(self,**kwargs):
        await self.manager.session.async_write_resource_device(self.device.did,self.rid,"0"); self.coordinator.data.setdefault("resources",{}).setdefault(self.device.did,{})[self.rid]="0"; self.async_write_ha_state(); await self.coordinator.async_request_refresh()
class AqaraTraitSwitch(AqaraCoordinatorEntity,SwitchEntity):
    def __init__(self,hass,dev,item): super().__init__(hass,dev,item["key"]); self.item=item; self._optimistic_value=None; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.trait_switch_{dev.did}_{item['key']}"
    @property
    def is_on(self):
        val=self._optimistic_value if self._optimistic_value is not None else self.trait_value(self.item["endpoint_id"],self.item["function_code"],self.item["trait_code"])
        return str(val).lower() in ("1","true","on")
    async def _write(self,value):
        resp=await self.manager.session.async_write_traits([{"deviceId":self.device.did,"endpointId":self.item["endpoint_id"],"functionCode":self.item["function_code"],"traitCode":self.item["trait_code"],"value":value}])
        if resp.get("code")==0:
            self._optimistic_value=value; self.coordinator.data.setdefault("traits",{})[(self.device.did,self.item["endpoint_id"],self.item["function_code"],self.item["trait_code"])]=value; self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
    async def async_turn_on(self,**kwargs): await self._write("1")
    async def async_turn_off(self,**kwargs): await self._write("0")
