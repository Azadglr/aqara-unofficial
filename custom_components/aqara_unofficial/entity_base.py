from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN,HASS_DATA_COORDINATOR,HASS_DATA_MANAGER
class AqaraCoordinatorEntity(CoordinatorEntity):
    def __init__(self,hass,device,key):
        super().__init__(hass.data[DOMAIN][HASS_DATA_COORDINATOR]); self.hass=hass; self.device=device; self._key=key; self._attr_device_info=device.device_info
    @property
    def manager(self): return self.hass.data[DOMAIN][HASS_DATA_MANAGER]
    def resource_value(self,rid): return (self.coordinator.data.get("resources") or {}).get(self.device.did,{}).get(rid)
    def trait_value(self,e,f,t): return (self.coordinator.data.get("traits") or {}).get((self.device.did,e,f,t))
