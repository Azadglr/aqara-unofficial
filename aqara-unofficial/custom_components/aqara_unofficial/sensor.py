from datetime import datetime, timezone
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTemperature
from .const import DOMAIN,DOORBELL_EVENT_HOLD_SECONDS,CAMERA_DETECTION_HOLD_SECONDS
from .entity_base import AqaraCoordinatorEntity
from .localize import name as lname,state as lstate
from .resource_definitions import DEVICE_RESOURCE_MAP,U200_MODEL,U200_POWER_TRAITS,CAMERA_TRAIT_MODEL
try:
    from homeassistant.helpers.entity import EntityCategory
except Exception: EntityCategory=None
async def async_setup_entry(hass,entry,async_add_entities):
    mgr=hass.data[DOMAIN]["aqara_manager"]; ents=[]
    for dev in mgr.get_devices_for_entry(entry.entry_id):
        ents.append(AqaraOnlineSensor(hass,dev))
        for item in DEVICE_RESOURCE_MAP.get(dev.model,{}).get("sensors",[]): ents.append(AqaraResourceSensor(hass,dev,item))
        if dev.model==U200_MODEL:
            for item in U200_POWER_TRAITS: ents.append(AqaraTraitSensor(hass,dev,item))
        if dev.model==CAMERA_TRAIT_MODEL: ents.append(AqaraCameraEventSensor(hass,dev,"human_detected","motion_detected","motion_detected"))
    async_add_entities(ents)
class AqaraOnlineSensor(AqaraCoordinatorEntity,SensorEntity):
    _attr_icon="mdi:lan-connect"
    def __init__(self,hass,dev): super().__init__(hass,dev,"online"); self._attr_name=f"{dev.device_name} {lname(hass,'online')}"; self._attr_unique_id=f"{DOMAIN}.online_{dev.did}"
    @property
    def native_value(self):
        v=(self.coordinator.data.get("devices") or {}).get(self.device.did,{}).get("online","unknown")
        return lstate(self.hass,"online" if v=="online" else "offline" if v=="offline" else "unknown")
class AqaraResourceSensor(AqaraCoordinatorEntity,SensorEntity):
    def __init__(self,hass,dev,item):
        super().__init__(hass,dev,item["key"]); self.item=item; self.rid=item["rid"]; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.sensor_{dev.did}_{item['key']}"
        if item.get("unit")=="%": self._attr_native_unit_of_measurement=PERCENTAGE
        elif item.get("unit")=="°C": self._attr_native_unit_of_measurement=UnitOfTemperature.CELSIUS
        if item.get("device_class"): self._attr_device_class=item["device_class"]
        if item.get("diagnostic"):
            self._attr_entity_registry_enabled_default=False
            if EntityCategory: self._attr_entity_category=EntityCategory.DIAGNOSTIC
    def _event_active(self):
        ts=(self.coordinator.data.get("events") or {}).get((self.device.did,self.rid,"ts"))
        try: ts=float(ts)
        except Exception: return False
        return datetime.now(timezone.utc).timestamp()-ts<=DOORBELL_EVENT_HOLD_SECONDS
    @property
    def native_value(self):
        if self.item.get("event_status")=="doorbell": return lstate(self.hass,"pressed" if self._event_active() else "clean")
        if self.item.get("event_status")=="tamper": return lstate(self.hass,"alarm" if self._event_active() else "safe")
        if self.item.get("event_status")=="problem": return lstate(self.hass,"problem" if self._event_active() else "ok")
        val=self.resource_value(self.rid)
        if self.item.get("face_map"):
            val=(self.coordinator.data.get("events") or {}).get((self.device.did,self.rid,"value"),val)
            if val in (None,"","unknown"): return lstate(self.hass,"unknown_person")
            return self.manager.face_map.get(str(val),str(val))
        try:
            val=float(val) if ("." in str(val) or self.item.get("scale")) else int(val)
            if self.item.get("scale"): val=round(val*self.item["scale"],2)
        except Exception: pass
        return val
class AqaraTraitSensor(AqaraCoordinatorEntity,SensorEntity):
    def __init__(self,hass,dev,item):
        super().__init__(hass,dev,item["key"]); self.item=item; self._attr_name=f"{dev.device_name} {lname(hass,item.get('label',item['key']))}"; self._attr_unique_id=f"{DOMAIN}.trait_{dev.did}_{item['key']}"
        if item.get("unit")=="%": self._attr_native_unit_of_measurement=PERCENTAGE
        elif item.get("unit")=="V": self._attr_native_unit_of_measurement=UnitOfElectricPotential.VOLT
        if item.get("device_class"): self._attr_device_class=item["device_class"]
    @property
    def native_value(self):
        val=self.trait_value(self.item["endpoint_id"],self.item["function_code"],self.item["trait_code"])
        if self.item.get("key")=="low_battery": return lstate(self.hass,"low" if str(val) in ("1","true","True") else "normal")
        try: return float(val)
        except Exception: return val
class AqaraCameraEventSensor(AqaraCoordinatorEntity,SensorEntity):
    _attr_icon="mdi:motion-sensor"
    def __init__(self,hass,dev,data_key,unique_key,label_key): super().__init__(hass,dev,unique_key); self.data_key=data_key; self._attr_name=f"{dev.device_name} {lname(hass,label_key)}"; self._attr_unique_id=f"{DOMAIN}.camera_event_{dev.did}_{unique_key}"
    @property
    def native_value(self):
        ts=(self.coordinator.data.get("camera_events") or {}).get((self.device.did,self.data_key,"ts"))
        try: ts=float(ts)
        except Exception: ts=None
        return lstate(self.hass,"detected" if ts and datetime.now(timezone.utc).timestamp()-ts<=CAMERA_DETECTION_HOLD_SECONDS else "not_detected")
