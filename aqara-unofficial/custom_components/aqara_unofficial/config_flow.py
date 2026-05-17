from __future__ import annotations
import json, logging
from datetime import datetime,timedelta,timezone
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from .aiot_cloud import AqaraCredentials,AqaraOpenApi
from .const import *
_LOGGER=logging.getLogger(__name__)
STEP_AUTH_SCHEMA=vol.Schema({vol.Required(CONF_FIELD_ACCOUNT):str,vol.Required(CONF_FIELD_COUNTRY_CODE,default=SERVER_COUNTRY_CODES_DEFAULT):vol.In(SERVER_COUNTRY_CODES),vol.Optional(CONF_FIELD_REFRESH_TOKEN):str,vol.Required("app_id"):str,vol.Required("key_id"):str,vol.Required("app_key"):str})
STEP_CODE_SCHEMA=vol.Schema({vol.Required(CONF_FIELD_AUTH_CODE):str})
def _mask(v,visible=4):
    v=str(v or ""); return v if len(v)<=visible*2 else f"{v[:visible]}{'*'*(len(v)-visible*2)}{v[-visible:]}"
class AqaraUnofficialFlowHandler(config_entries.ConfigFlow,domain=DOMAIN):
    VERSION=1
    def __init__(self): self._account=None; self._country=None; self._creds=None; self._client=None; self._token_result=None
    @staticmethod
    def async_get_options_flow(config_entry): return AqaraUnofficialOptionsFlowHandler(config_entry)
    async def async_step_user(self,user_input=None):
        errors={}
        if user_input:
            self._account=user_input[CONF_FIELD_ACCOUNT].strip(); self._country=user_input[CONF_FIELD_COUNTRY_CODE]; self._creds=AqaraCredentials(user_input["app_id"].strip(),user_input["key_id"].strip(),user_input["app_key"].strip()); self._client=AqaraOpenApi(self.hass,self._creds,country_code=self._country); refresh=(user_input.get(CONF_FIELD_REFRESH_TOKEN) or "").strip()
            try:
                if refresh:
                    r=await self._client.async_refresh_token(refresh)
                    if r.get("code")==0: self._token_result=r.get("result"); return await self.async_step_select_devices()
                    errors["base"]="refresh_failed"
                else:
                    r=await self._client.async_get_auth_code(self._account,0)
                    if r.get("code")==0: return await self.async_step_code()
                    errors["base"]="auth_code_failed"
            except Exception as ex: _LOGGER.debug("Auth step failed: %s",ex); errors["base"]="auth_code_failed"
        return self.async_show_form(step_id="user",data_schema=STEP_AUTH_SCHEMA,errors=errors)
    async def async_step_code(self,user_input=None):
        errors={}
        if user_input and self._client and self._account:
            r=await self._client.async_get_token(user_input[CONF_FIELD_AUTH_CODE].strip(),self._account,0)
            if r.get("code")==0: self._token_result=r.get("result"); return await self.async_step_select_devices()
            errors["base"]="token_failed"
        return self.async_show_form(step_id="code",data_schema=STEP_CODE_SCHEMA,errors=errors)
    async def async_step_select_devices(self,user_input=None):
        if not self._client or not self._token_result or not self._creds or not self._account or not self._country: return self.async_abort(reason="not_authenticated")
        self._client.set_tokens(self._token_result.get("accessToken"),self._token_result.get("refreshToken"))
        if user_input:
            selected=user_input.get(CONF_FIELD_SELECTED_DEVICES) or []; exp=""
            try:
                if self._token_result.get("expiresIn"): exp=(datetime.now(timezone.utc)+timedelta(seconds=int(self._token_result.get("expiresIn")))).isoformat()
            except Exception: pass
            data={"app_id":self._creds.app_id,"key_id":self._creds.key_id,"app_key":self._creds.app_key,CONF_ENTRY_AUTH_ACCOUNT:self._account,CONF_ENTRY_AUTH_ACCOUNT_TYPE:0,CONF_ENTRY_AUTH_COUNTRY_CODE:self._country,CONF_ENTRY_AUTH_OPENID:self._token_result.get("openId"),CONF_ENTRY_AUTH_ACCESS_TOKEN:self._token_result.get("accessToken"),CONF_ENTRY_AUTH_REFRESH_TOKEN:self._token_result.get("refreshToken"),CONF_ENTRY_AUTH_EXPIRES_IN:self._token_result.get("expiresIn"),CONF_ENTRY_AUTH_EXPIRES_TIME:exp,CONF_ENTRY_SELECTED_DEVICES:list(selected),CONF_ENTRY_FACE_MAP:"{}"}
            await self.async_set_unique_id(f"aqara_unofficial_{data.get(CONF_ENTRY_AUTH_OPENID) or self._account}"); self._abort_if_unique_id_configured(); return self.async_create_entry(title=_mask(self._account,4),data=data)
        devices=await self._client.async_query_all_devices(); devlist={d.get("did"):f"{d.get('deviceName') or d.get('did')} - {d.get('model')}" for d in devices if d.get("did")}
        return self.async_show_form(step_id="select_devices",data_schema=vol.Schema({vol.Required(CONF_FIELD_SELECTED_DEVICES,default=[]):cv.multi_select(devlist)}),errors={})
class AqaraUnofficialOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self,entry): self.entry=entry
    async def async_step_init(self,user_input=None):
        errors={}
        if user_input is not None:
            m=self._lines_to_map(user_input.get(CONF_FIELD_FACE_MAP_LINES) or "")
            if m is None: errors[CONF_FIELD_FACE_MAP_LINES]="invalid_json"
            if not errors: return self.async_create_entry(title="",data={CONF_ENTRY_SELECTED_DEVICES:list(user_input.get(CONF_FIELD_SELECTED_DEVICES) or []),CONF_ENTRY_FACE_MAP:json.dumps(m,ensure_ascii=False)})
        creds=AqaraCredentials(self.entry.data.get("app_id") or "",self.entry.data.get("key_id") or "",self.entry.data.get("app_key") or ""); client=AqaraOpenApi(self.hass,creds,country_code=self.entry.data.get("country_code","GER")); client.set_tokens(self.entry.data.get("access_token"),self.entry.data.get("refresh_token"))
        devices=[]; devlist={}
        try:
            devices=await client.async_query_all_devices(); devlist={d.get("did"):f"{d.get('deviceName') or d.get('did')} - {d.get('model')}" for d in devices if d.get("did")}
        except Exception as ex: _LOGGER.debug("Device query failed in options flow: %s",ex); errors["base"]="device_query_failed"
        current=(self.entry.options or {}).get(CONF_ENTRY_SELECTED_DEVICES)
        if current is None: current=self.entry.data.get(CONF_ENTRY_SELECTED_DEVICES) or []
        try: face_map=json.loads((self.entry.options or {}).get(CONF_ENTRY_FACE_MAP) or self.entry.data.get(CONF_ENTRY_FACE_MAP) or "{}")
        except Exception: face_map={}
        for d in devices:
            if d.get("did") in current and d.get("model")=="lumi.camera.agl002":
                try:
                    hist=await client.async_fetch_resource_history(d.get("did"),["13.95.85"],size=20)
                    for item in self._flatten(hist):
                        if str(item.get("resourceId"))=="13.95.85" and item.get("value") not in (None,""): face_map.setdefault(str(item.get("value")),"Name")
                except Exception: pass
        return self.async_show_form(step_id="init",data_schema=vol.Schema({vol.Required(CONF_FIELD_SELECTED_DEVICES,default=list(current)):cv.multi_select(devlist),vol.Optional(CONF_FIELD_FACE_MAP_LINES,default=self._map_to_lines(face_map)):str}),errors=errors)
    @staticmethod
    def _map_to_lines(m): return "\n".join(f"{k} = {v}" for k,v in (m or {}).items())
    @staticmethod
    def _lines_to_map(text):
        out={}
        for line in str(text or "").splitlines():
            line=line.strip()
            if not line: continue
            if "=" not in line: return None
            k,v=line.split("=",1); k=k.strip(); v=v.strip()
            if not k: return None
            out[k]=v or "Name"
        return out
    @staticmethod
    def _flatten(resp):
        raw=resp.get("result",[]) if isinstance(resp,dict) else []
        if isinstance(raw,list): return [x for x in raw if isinstance(x,dict)]
        if isinstance(raw,dict):
            for k in ("data","attributes","list","items","result"):
                if isinstance(raw.get(k),list): return [x for x in raw[k] if isinstance(x,dict)]
        return []
