import logging
from homeassistant.components.lock import LockEntity,LockEntityFeature
from .const import DOMAIN
from .entity_base import AqaraCoordinatorEntity
from .resource_definitions import U200_MODEL,U200_LOCK
_LOGGER=logging.getLogger(__name__)
async def async_setup_entry(hass,entry,async_add_entities):
    mgr=hass.data[DOMAIN]["aqara_manager"]; async_add_entities([AqaraU200Lock(hass,dev) for dev in mgr.get_devices_for_entry(entry.entry_id) if dev.model==U200_MODEL])
class AqaraU200Lock(AqaraCoordinatorEntity,LockEntity):
    _attr_supported_features=LockEntityFeature.OPEN
    def __init__(self,hass,dev): super().__init__(hass,dev,"lock"); self._attr_name=dev.device_name; self._attr_unique_id=f"{DOMAIN}.lock_{dev.did}"; self._attr_is_opening=False
    @property
    def is_locked(self): return str(self.trait_value(U200_LOCK["endpoint_id"],U200_LOCK["function_code"],U200_LOCK["trait_code"]))=="1"
    @property
    def is_opening(self): return self._attr_is_opening
    async def async_lock(self,**kwargs): await self._write("1","lock")
    async def async_unlock(self,**kwargs): await self._write("2","unlock")
    async def async_open(self,**kwargs): self._attr_is_opening=True; self.async_write_ha_state(); await self._write("2","open"); self._attr_is_opening=False; self.async_write_ha_state()
    async def _write(self,value,action):
        resp=await self.manager.session.async_write_traits([{"deviceId":self.device.did,"endpointId":U200_LOCK["endpoint_id"],"functionCode":U200_LOCK["function_code"],"traitCode":U200_LOCK["trait_code"],"value":value}])
        if resp.get("code")!=0: _LOGGER.error("U200 %s action failed: %s",action,resp)
        await self.coordinator.async_request_refresh()
