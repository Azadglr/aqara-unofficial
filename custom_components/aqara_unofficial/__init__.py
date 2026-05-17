from __future__ import annotations
from homeassistant.helpers import config_validation as cv
import json, logging, time
from pathlib import Path
from typing import Any
from .aiot_cloud import AqaraCredentials,AqaraOpenApi
from .aiot_manager import AiotManager,AqaraDataCoordinator
from .const import DOMAIN,HASS_DATA_COORDINATOR,HASS_DATA_MANAGER,PLATFORMS
_LOGGER=logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CAMERA_EVENT_RESOURCE_IDS=([f"13.{i}.85" for i in range(1,181)]+[f"4.{i}.85" for i in range(1,181)]+[f"14.{i}.85" for i in range(1,181)]+["13.95.85","13.12.85","13.9.85","13.10.85","13.11.85","13.97.85"])
async def async_setup(hass,config): hass.data.setdefault(DOMAIN,{}); return True
async def _async_update_listener(hass,entry): await hass.config_entries.async_reload(entry.entry_id)
async def async_setup_entry(hass,entry):
    hass.data.setdefault(DOMAIN,{}); creds=AqaraCredentials(entry.data.get("app_id") or "",entry.data.get("key_id") or "",entry.data.get("app_key") or ""); client=AqaraOpenApi(hass,creds,country_code=entry.data.get("country_code","GER")); client.set_tokens(entry.data.get("access_token"),entry.data.get("refresh_token"))
    manager=AiotManager(hass,client); await manager.async_register_entry(entry); coordinator=AqaraDataCoordinator(hass,manager,entry); await coordinator.async_config_entry_first_refresh(); hass.data[DOMAIN][HASS_DATA_MANAGER]=manager; hass.data[DOMAIN][HASS_DATA_COORDINATOR]=coordinator; entry.async_on_unload(entry.add_update_listener(_async_update_listener)); await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS)
    async def dump_qlink_traits(call): await coordinator.async_dump_qlink_traits()
    async def discover_camera_events(call): await _discover_camera_events(hass,entry,manager,call)
    hass.services.async_register(DOMAIN,"dump_qlink_traits",dump_qlink_traits); hass.services.async_register(DOMAIN,"discover_camera_events",discover_camera_events); return True
async def async_unload_entry(hass,entry):
    ok=await hass.config_entries.async_unload_platforms(entry,PLATFORMS)
    if ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(HASS_DATA_MANAGER,None); hass.data[DOMAIN].pop(HASS_DATA_COORDINATOR,None)
        for svc in ("dump_qlink_traits","discover_camera_events"):
            if hass.services.has_service(DOMAIN,svc): hass.services.async_remove(DOMAIN,svc)
    return ok
async def _discover_camera_events(hass,entry,manager,call):
    size=int(call.data.get("size",50)); batch_size=int(call.data.get("batch_size",20)); include_all=bool(call.data.get("include_all",False)); devices=manager.get_devices_for_entry(entry.entry_id); output={"created_at":int(time.time()),"devices":{}}
    for device in devices:
        if not str(device.model or "").startswith("lumi.camera"): continue
        dout={"name":device.device_name,"model":device.model,"resources":{}}
        for chunk in _chunks(CAMERA_EVENT_RESOURCE_IDS,batch_size):
            try: resp=await manager.session.async_fetch_resource_history(device.did,list(chunk),size=size)
            except Exception as ex: dout["resources"][",".join(chunk)]={"error":str(ex)}; continue
            flat=_flatten_history_response(resp)
            if flat or include_all:
                for item in flat: dout["resources"].setdefault(str(item.get("resourceId")),[]).append(item)
                if include_all and not flat: dout["resources"][",".join(chunk)]=resp
        output["devices"][device.did]=dout
    path=Path(hass.config.path(f"aqara_unofficial_camera_events_{int(time.time())}.json")); path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8"); _LOGGER.info("Aqara camera event discovery written to %s",path)
def _flatten_history_response(resp:dict[str,Any])->list[dict[str,Any]]:
    raw=resp.get("result",[]) if isinstance(resp,dict) else []
    if isinstance(raw,list): return [x for x in raw if isinstance(x,dict)]
    if isinstance(raw,dict):
        for k in ("data","attributes","list","items","result","resources"):
            if isinstance(raw.get(k),list): return [x for x in raw[k] if isinstance(x,dict)]
    return []
def _chunks(items,size):
    for i in range(0,len(items),size): yield items[i:i+size]
