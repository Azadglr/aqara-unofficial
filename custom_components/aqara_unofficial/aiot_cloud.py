from __future__ import annotations
import hashlib, json, logging, random, string, time
from dataclasses import dataclass
from typing import Any
from aiohttp import ClientTimeout
from homeassistant.helpers import aiohttp_client
_LOGGER = logging.getLogger(__name__)
API_DOMAIN = {"CN":"open-cn.aqara.com","USA":"open-usa.aqara.com","KR":"open-kr.aqara.com","RU":"open-ru.aqara.com","GER":"open-ger.aqara.com","SG":"open-sg.aqara.com"}
def _nonce(length:int=16)->str: return "".join(random.choice(string.ascii_letters+string.digits) for _ in range(length))
def _md5(value:str)->str: return hashlib.md5(value.encode()).hexdigest()
def gen_sign(token:str|None, app_id:str, key_id:str, nonce:str, timestamp:str, app_key:str)->str:
    parts=[]
    if token: parts.append(f"Accesstoken={token}")
    parts.extend([f"Appid={app_id}", f"Keyid={key_id}", f"Nonce={nonce}", f"Time={timestamp}"])
    return _md5(("&".join(parts)+app_key).lower())
@dataclass(slots=True)
class AqaraCredentials:
    app_id:str; key_id:str; app_key:str
class AqaraOpenApi:
    def __init__(self,hass,creds:AqaraCredentials,country_code="GER",lang="en"):
        self._hass=hass; self._creds=creds; self._country=country_code; self._lang=lang; self.access_token=None; self.refresh_token=None
    def set_tokens(self,access_token,refresh_token): self.access_token=access_token; self.refresh_token=refresh_token
    @property
    def endpoint(self): return f"https://{API_DOMAIN[self._country]}/v3.0/open/api"
    def _session(self): return aiohttp_client.async_get_clientsession(self._hass)
    def _headers(self,use_token=True):
        nonce=_nonce(); ts=str(int(time.time()*1000)); token=self.access_token if use_token else None
        h={"Appid":self._creds.app_id,"Keyid":self._creds.key_id,"Nonce":nonce,"Time":ts,"Sign":gen_sign(token,self._creds.app_id,self._creds.key_id,nonce,ts,self._creds.app_key),"Content-Type":"application/json"}
        if self._lang: h["Lang"]=self._lang
        if token: h["Accesstoken"]=token
        return h
    async def _post(self,intent,data,use_token=True):
        payload=json.dumps({"intent":intent,"data":data},separators=(",",":"))
        async with self._session().post(self.endpoint,data=payload,headers=self._headers(use_token),timeout=ClientTimeout(total=30)) as resp:
            text=await resp.text()
            try: out=json.loads(text) if text else {"code":resp.status,"message":"Empty response"}
            except json.JSONDecodeError: out={"code":resp.status,"message":text or "Invalid JSON response"}
            if out.get("code") not in (0,None): _LOGGER.debug("Aqara API non-zero response for %s: %s", intent, out)
            return out
    async def async_get_auth_code(self,account,account_type=0,access_token_validity="7d"):
        return await self._post("config.auth.getAuthCode",{"account":account,"accountType":account_type,"accessTokenValidity":access_token_validity},False)
    async def async_get_token(self,code,account,account_type=0):
        r=await self._post("config.auth.getToken",{"authCode":code,"account":account,"accountType":account_type},False)
        if r.get("code")==0 and r.get("result"): self.set_tokens(r["result"].get("accessToken"),r["result"].get("refreshToken"))
        return r
    async def async_refresh_token(self,refresh_token):
        r=await self._post("config.auth.refreshToken",{"refreshToken":refresh_token},False)
        if r.get("code")==0 and r.get("result"): self.set_tokens(r["result"].get("accessToken"),r["result"].get("refreshToken"))
        return r
    async def async_query_device_info(self,dids=None,position_id="",page_num=1,page_size=50):
        d={"positionId":position_id,"pageNum":page_num,"pageSize":page_size}
        if dids: d["dids"]=dids
        return await self._post("query.device.info",d,True)
    async def async_query_all_devices(self):
        out=[]; page=1
        while True:
            r=await self.async_query_device_info(page_num=page,page_size=50)
            if r.get("code")!=0: raise RuntimeError(r.get("message") or "query.device.info failed")
            res=r.get("result") or {}; data=res.get("data") or []; total=int(res.get("totalCount") or len(data)); out.extend(data)
            if len(out)>=total or not data: break
            page+=1
        return out
    async def async_query_resource_value(self,subject_id,resource_ids=None):
        o={"subjectId":subject_id}
        if resource_ids: o["resourceIds"]=resource_ids
        return await self._post("query.resource.value",{"resources":[o]},True)
    async def async_write_resource_device(self,subject_id,rid,value):
        return await self._post("write.resource.device",[{"subjectId":subject_id,"resources":[{"resourceId":rid,"value":str(value)}]}],True)
    async def async_fetch_resource_history(self,subject_id,resource_ids,size=20):
        return await self._post("fetch.resource.history",{"subjectId":subject_id,"resourceIds":resource_ids,"startTime":1514736000000,"endTime":int(time.time()*1000),"size":size,"scanId":""},True)
    async def async_query_traits(self,traits): return await self._post("spec.query.trait",{"traits":traits},True)
    async def async_write_traits(self,traits): return await self._post("spec.write.trait",{"traits":traits},True)
    async def async_query_qlinkmodel_config(self,models): return await self._post("spec.query.qlinkmodel.config",{"models":models},True)
