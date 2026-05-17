from datetime import datetime, timezone
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN,DOORBELL_EVENT_HOLD_SECONDS
from .entity_base import AqaraCoordinatorEntity
from .localize import name as lname
from .resource_definitions import DEVICE_RESOURCE_MAP,CAMERA_TRAIT_MODEL,CAMERA_TRAIT_BINARY_SENSORS
try:
    from homeassistant.helpers.entity import EntityCategory
except Exception: EntityCategory=None
async def async_setup_entry(hass,entry,async_add_entities):
    mgr=hass.data[DOMAIN]["aqara_manager"]; ents=[]
    for dev in mgr.get_devices_for_entry(entry.entry_id):
        for item in DEVICE_RESOURCE_MAP.get(dev.model,{}).get("binary_sensors",[]): ents.append(AqaraResourceBinarySensor(hass,dev,item))
        if dev.model==CAMERA_TRAIT_MODEL:
            for item in CAMERA_TRAIT_BINARY_SENSORS: ents.append(AqaraTraitBinarySensor(hass,dev,item))
    async_add_entities(ents)
class AqaraResourceBinarySensor(AqaraCoordinatorEntity,BinarySensorEntity):
    def __init__(self,hass,dev,item):
        super().__init__(hass,dev,item["key"]); self.item=item; self.rid=item["rid"]; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.binary_{dev.did}_{item['key']}"
        if item.get("diagnostic"):
            self._attr_entity_registry_enabled_default=False
            if EntityCategory: self._attr_entity_category=EntityCategory.DIAGNOSTIC
    @property
    def is_on(self):
        if self.item.get("auto_reset"):
            ts=(self.coordinator.data.get("events") or {}).get((self.device.did,self.rid,"ts"))
            try: ts=float(ts)
            except Exception: return False
            return datetime.now(timezone.utc).timestamp()-ts<=DOORBELL_EVENT_HOLD_SECONDS
        return str(self.resource_value(self.rid))==str(self.item.get("on","1"))
class AqaraTraitBinarySensor(AqaraCoordinatorEntity,BinarySensorEntity):
    def __init__(self,hass,dev,item): super().__init__(hass,dev,item["key"]); self.item=item; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.trait_binary_{dev.did}_{item['key']}"
    @property
    def is_on(self): return False
