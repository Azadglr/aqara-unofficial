from __future__ import annotations
import json, logging, time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN,EVENT_SCAN_INTERVAL_SECONDS,RESOURCE_SCAN_INTERVAL_SECONDS
from .resource_definitions import CAMERA_HUMAN_EVENT_RID,CAMERA_TRAIT_MODEL,DEVICE_RESOURCE_MAP,U200_LOCK,U200_MODEL,U200_POWER_TRAITS
_LOGGER=logging.getLogger(__name__)
DOORBELL_MODEL="lumi.camera.agl002"; FACE_RID="13.95.85"; EVENT_RIDS=["13.12.85","13.9.85","13.10.85","13.11.85","13.95.85"]
@dataclass(slots=True)
class AiotDevice:
    did:str; parent_did:str|None; model:str; model_type:int|None; device_name:str; state:int|None; timezone:str|None; firmware_version:str|None
    @classmethod
    def from_api(cls,r): return cls(r.get("did"),r.get("parentDid"),r.get("model"),r.get("modelType"),r.get("deviceName") or r.get("did"),r.get("state"),r.get("timeZone"),r.get("firmwareVersion"))
    @property
    def device_info(self): return DeviceInfo(identifiers={(DOMAIN,self.did)},name=self.device_name,model=self.model,manufacturer=(self.model or "Aqara").split(".",1)[0].capitalize(),sw_version=self.firmware_version)
class AiotManager:
    def __init__(self,hass,session): self.hass=hass; self.session=session; self._all_devices={}; self._entry_devices={}; self.face_map={}
    async def async_refresh_all_devices(self): self._all_devices={d["did"]:AiotDevice.from_api(d) for d in await self.session.async_query_all_devices() if d.get("did")}
    def get_devices_for_entry(self,eid): return [self._all_devices[d] for d in self._entry_devices.get(eid,[]) if d in self._all_devices]
    async def async_register_entry(self,entry):
        await self.async_refresh_all_devices(); sel=(entry.options or {}).get("selected_devices")
        if sel is None: sel=entry.data.get("selected_devices") or []
        self._entry_devices[entry.entry_id]=list(sel); self.face_map=self._load_face_map(entry)
    def _load_face_map(self,entry):
        raw=(entry.options or {}).get("face_map_json") or entry.data.get("face_map_json")
        if raw:
            try: return json.loads(raw)
            except Exception: _LOGGER.warning("Invalid face map JSON; falling back to file")
        p=Path(self.hass.config.path("aqara_unofficial_face_map.json"))
        if not p.exists(): p.write_text(json.dumps({"1328531273258582016":"Known Person"},ensure_ascii=False,indent=2),encoding="utf-8")
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return {}
class AqaraDataCoordinator(DataUpdateCoordinator):
    def __init__(self,hass,manager,entry):
        super().__init__(hass,_LOGGER,name="aqara_unofficial",update_interval=timedelta(seconds=EVENT_SCAN_INTERVAL_SECONDS))
        self.manager=manager; self.entry=entry; self._last_resource=0.0; self.data={"resources":{},"traits":{},"devices":{},"events":{},"camera_events":{}}
    async def _async_update_data(self):
        data={k:dict((self.data or {}).get(k) or {}) for k in ("resources","traits","devices","events","camera_events")}
        devices=self.manager.get_devices_for_entry(self.entry.entry_id); now=time.time()
        await self._refresh_event_history(devices,data)
        if now-self._last_resource<RESOURCE_SCAN_INTERVAL_SECONDS: return data
        self._last_resource=now
        try:
            await self.manager.async_refresh_all_devices(); sel=(self.entry.options or {}).get("selected_devices")
            if sel is None: sel=self.entry.data.get("selected_devices") or []
            self.manager._entry_devices[self.entry.entry_id]=list(sel); self.manager.face_map=self.manager._load_face_map(self.entry); devices=self.manager.get_devices_for_entry(self.entry.entry_id)
        except Exception as ex: _LOGGER.debug("Device list refresh failed: %s",ex)
        for dev in devices: data["devices"][dev.did]={"online":"online" if dev.state==1 else "offline"}
        await self._refresh_resources(devices,data); await self._refresh_traits(devices,data); return data
    async def _refresh_event_history(self,devices,data):
        for dev in devices:
            if dev.model==DOORBELL_MODEL:
                try:
                    r=await self.manager.session.async_fetch_resource_history(dev.did,EVENT_RIDS,size=20)
                    if r.get("code")==0:
                        for it in self._flatten(r):
                            rid=str(it.get("resourceId")); val=it.get("value"); ts=self._timestamp(it)
                            if not ts: continue
                            if rid in ("13.12.85","13.9.85","13.10.85","13.11.85") and str(val)=="1": data["events"][(dev.did,rid,"ts")]=max(ts,data["events"].get((dev.did,rid,"ts")) or 0)
                            if rid==FACE_RID and val not in (None,"") and ts>=data["events"].get((dev.did,rid,"ts"),0): data["events"][(dev.did,rid,"ts")]=ts; data["events"][(dev.did,rid,"value")]=str(val)
                except Exception as ex: _LOGGER.debug("Doorbell history refresh failed for %s: %s",dev.did,ex)
            if dev.model==CAMERA_TRAIT_MODEL:
                try:
                    r=await self.manager.session.async_fetch_resource_history(dev.did,[CAMERA_HUMAN_EVENT_RID],size=5)
                    if r.get("code")==0:
                        for it in self._flatten(r):
                            ts=self._timestamp(it)
                            if str(it.get("resourceId"))==CAMERA_HUMAN_EVENT_RID and str(it.get("value"))=="1" and ts: data["camera_events"][(dev.did,"human_detected","ts")]=max(ts,data["camera_events"].get((dev.did,"human_detected","ts")) or 0)
                except Exception as ex: _LOGGER.debug("Camera event history refresh failed for %s: %s",dev.did,ex)
    async def _refresh_resources(self,devices,data):
        for dev in devices:
            cfg=DEVICE_RESOURCE_MAP.get(dev.model,{}); rids=[]
            for k in ("switches","numbers","sensors","binary_sensors"): rids += [i["rid"] for i in cfg.get(k,[])]
            if not rids: continue
            try:
                r=await self.manager.session.async_query_resource_value(dev.did,sorted(set(rids)))
                if r.get("code")==0:
                    res=r.get("result") or []
                    if isinstance(res,dict): res=res.get("resources") or res.get("data") or []
                    data["resources"].setdefault(dev.did,{})
                    for it in res:
                        if it.get("resourceId") is not None: data["resources"][dev.did][it.get("resourceId")]=it.get("value")
            except Exception as ex: _LOGGER.debug("Resource refresh failed for %s: %s",dev.did,ex)
    async def _refresh_traits(self,devices,data):
        traits=[]
        for dev in devices:
            if dev.model==U200_MODEL:
                traits.append({"deviceId":dev.did,"endpointId":U200_LOCK["endpoint_id"],"functionCode":U200_LOCK["function_code"],"traitCode":U200_LOCK["trait_code"]})
                for t in U200_POWER_TRAITS: traits.append({"deviceId":dev.did,"endpointId":t["endpoint_id"],"functionCode":t["function_code"],"traitCode":t["trait_code"]})
        if not traits: return
        try:
            r=await self.manager.session.async_query_traits(traits)
            if r.get("code")==0:
                for it in (r.get("result") or {}).get("data") or []: data["traits"][(it.get("deviceId"),it.get("endpointId"),it.get("functionCode"),it.get("traitCode"))]=it.get("value")
        except Exception as ex: _LOGGER.debug("Trait refresh failed: %s",ex)
    @staticmethod
    def _flatten(r):
        raw=r.get("result",[]) if isinstance(r,dict) else []
        if isinstance(raw,list): return [x for x in raw if isinstance(x,dict)]
        if isinstance(raw,dict):
            for k in ("data","attributes","list","items","result","resources"):
                if isinstance(raw.get(k),list): return [x for x in raw[k] if isinstance(x,dict)]
        return []
    @staticmethod
    def _timestamp(it):
        ts=it.get("timeStamp") or it.get("timestamp") or it.get("time")
        try: ts=float(ts)
        except Exception: return None
        return ts/1000 if ts>1000000000000 else ts
    async def async_dump_qlink_traits(self):
        models=sorted({d.model for d in self.manager.get_devices_for_entry(self.entry.entry_id) if d.model and not d.model.startswith("aqara.matter")}); out={"models":models,"responses":{}}
        for i in range(0,len(models),5):
            chunk=models[i:i+5]; out["responses"][",".join(chunk)]=await self.manager.session.async_query_qlinkmodel_config(chunk)
        Path(self.manager.hass.config.path("aqara_unofficial_qlink_traits.json")).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
