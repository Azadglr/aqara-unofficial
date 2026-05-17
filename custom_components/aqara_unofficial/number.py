from homeassistant.components.number import NumberEntity
from .const import DOMAIN
from .entity_base import AqaraCoordinatorEntity
from .localize import name as lname
from .resource_definitions import DEVICE_RESOURCE_MAP
async def async_setup_entry(hass,entry,async_add_entities):
    mgr=hass.data[DOMAIN]["aqara_manager"]; ents=[]
    for dev in mgr.get_devices_for_entry(entry.entry_id):
        for item in DEVICE_RESOURCE_MAP.get(dev.model,{}).get("numbers",[]): ents.append(AqaraResourceNumber(hass,dev,item))
    async_add_entities(ents)
class AqaraResourceNumber(AqaraCoordinatorEntity,NumberEntity):
    def __init__(self,hass,dev,item):
        super().__init__(hass,dev,item["key"]); self.item=item; self.rid=item["rid"]; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.number_{dev.did}_{item['key']}"; self._attr_native_min_value=item.get("min",0); self._attr_native_max_value=item.get("max",100); self._attr_native_step=item.get("step",1)
    @property
    def native_value(self):
        try: return float(self.resource_value(self.rid))
        except Exception: return None
    async def async_set_native_value(self,value): await self.manager.session.async_write_resource_device(self.device.did,self.rid,str(int(value))); await self.coordinator.async_request_refresh()
