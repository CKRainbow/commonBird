import json
import os
import asyncio
import datetime
from typing import Dict
from enum import Enum

import httpx
from dotenv import load_dotenv
from ebird.api.validation import (
    clean_back,
    clean_dist,
    clean_lat,
    clean_lng,
    clean_location,
    clean_region,
)
from ebird.api.hotspots import REGION_HOTSPOTS_URL
from ebird.api.regions import REGION_LIST_URL

from src import database_path


class RegionType(Enum):
    COUNTRY = "country"
    SUBNATIONAL1 = "subnational1"
    SUBNATIONAL2 = "subnational2"


async def call(url: str, params: Dict, headers: Dict) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        res = response.json()
    return res


class EBird:
    def __init__(self, token, locale="zh_SIM"):
        self.token = token
        self.locale = locale

    @classmethod
    async def create(cls, token: str):
        instance = cls(token)
        res = await instance.get_regions(RegionType.SUBNATIONAL1, "MO")
        print(res)
        return instance

    async def get_hotspots(self, region: str, back: int = None):
        url = REGION_HOTSPOTS_URL % clean_region(region)
        params = {
            "fmt": "json",
        }
        if back is not None:
            params["back"] = clean_back(back)
        headers = {"X-eBirdApiToken": self.token}

        res = await call(url, params, headers)
        return res

    async def update_cn_hotspots(self):
        res = await self.get_hotspots("CN")
        res = {hotspot["locName"]: hotspot for hotspot in res}
        res["latest_update_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        old_cn_hotspots = database_path / "ebird_cn_hotspots.json"
        old_cn_hotspots_bak = old_cn_hotspots.with_suffix(".json.bak")
        if old_cn_hotspots_bak.exists():
            os.remove(old_cn_hotspots_bak)
        os.rename(old_cn_hotspots, old_cn_hotspots.with_suffix(".json.bak"))
        with open(old_cn_hotspots, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        tw_res = await self.get_hotspots("TW")
        hk_res = await self.get_hotspots("HK")
        mo_res = await self.get_hotspots("MO")
        res = tw_res + hk_res + mo_res
        res = {hotspot["locName"]: hotspot for hotspot in res}
        res["latest_update_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        old_other_hotspots = database_path / "ebird_other_hotspots.json"
        old_other_hotspots_bak = old_other_hotspots.with_suffix(".json.bak")
        if old_other_hotspots_bak.exists():
            os.remove(old_other_hotspots_bak)
        os.rename(old_other_hotspots, old_other_hotspots.with_suffix(".json.bak"))
        with open(old_other_hotspots, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

    async def get_regions(self, region_type: RegionType, region: str):
        url = REGION_LIST_URL % (region_type.value, clean_region(region))

        params = {"fmt": "json", "locale": self.locale}

        headers = {
            "X-eBirdApiToken": self.token,
        }

        res = await call(url, params, headers)
        return res


if __name__ == "__main__":
    load_dotenv()
    ebird = EBird(os.getenv("EBIRD_TOKEN"))

    async def inner():
        # result = []
        # result.extend(await ebird.get_hotspots("MO"))
        # result.extend(await ebird.get_hotspots("HK"))
        # result.extend(await ebird.get_hotspots("TW"))
        result = []
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "CN"))
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "MO"))
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "HK"))
        result.extend(await ebird.get_regions(RegionType.SUBNATIONAL1, "TW"))
        return result

    result = asyncio.run(inner())

    with open("regions.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

# class ebird:
#     def __init__(self, token, locale='zh_SIM'):
#         self.token = token
#         self.locale = locale

#     spp_dict = {}
#     spp_trans = {}
#     with open("./ebird-CN.json", "r", encoding="utf-8") as f:
#         spp_db = json.loads(f.read())
#     for _spp in spp_db:
#         # 消除 例如 灰喜鹊、灰喜鹊（东亚）这样的重复
#         if 'reportAs' in _spp:
#             spp_dict[_spp['speciesCode']] = spp_dict[_spp['reportAs']]
#         else:
#             spp_dict[_spp['speciesCode']] = (_spp['sciName'], _spp['comName'])
#         spp_trans[_spp['sciName']] = (_spp['comName'], _spp['speciesCode'])

#     def update_spp(self, speciesCode):
#         if speciesCode not in self.spp_dict:
#             spp = self.query_species(speciesCode)
#             self.spp_db.append(spp[0])
#             f = open('./ebird-CN.json','w+')
#             ll = json.dumps(self.spp_db,sort_keys=True, indent=4, separators=(',', ': '))
#             f.write(ll)
#             f.close()
#             self.spp_dict[speciesCode] = (spp[0]['sciName'], spp[0]['comName'])
#             self.spp_trans[spp[0]['sciName']] = (spp[0]['comName'], spp[0]['speciesCode'])

#     def query_species(self, specie):
#         url = f"https://api.ebird.org/v2/ref/taxonomy/ebird?species={specie}&locale=zh_SIM&fmt=json"
#         payload={}
#         headers = {
#             'X-eBirdApiToken': self.token
#         }
#         response = requests.request("GET", url, headers=headers, data=payload)
#         res = response.text
#         return json.loads(res)

#     def get_sciName_from_speciesCode(self, speciesCode):
#         self.update_spp(speciesCode)
#         return self.spp_dict[speciesCode][0]

#     def get_comName_from_speciesCode(self, speciesCode):
#         self.update_spp(speciesCode)
#         return self.spp_dict[speciesCode][1]

#     def get_comName_from_sciName(self, sciName):
#         return self.spp_trans[sciName][0]

#     def get_speciesCode_from_sciName(self, sciName):
#         return self.spp_trans[sciName][1]

#     def get_recent_obs(self, regionCode='CN-11',back=7):
#         url = f"https://api.ebird.org/v2/data/obs/{regionCode}/recent?back={back}&sppLocale={self.locale}"
#         payload={}
#         headers = {
#             'X-eBirdApiToken': self.token
#         }
#         response = requests.request("GET", url, headers=headers, data=payload)
#         res = response.text
#         return json.loads(res)

#     def get_historic_obs(self, regionCode='CN-11', date=''):
#         url = f"https://api.ebird.org/v2/data/obs/{regionCode}/historic/{date}?sppLocale={self.locale}"
#         payload={}
#         headers = {
#             'X-eBirdApiToken': self.token
#         }
#         response = requests.request("GET", url, headers=headers, data=payload)
#         res = response.text
#         return json.loads(res)

#     def get_historic_list(self, regionCode='CN-11', date=''):
#         url = f"https://api.ebird.org/v2/product/lists/{regionCode}/{date}"
#         payload={}
#         headers = {
#             'X-eBirdApiToken': self.token
#         }
#         response = requests.request("GET", url, headers=headers, data=payload)
#         res = response.text
#         return json.loads(res)

#     def get_report_detail(self, subId):
#         url = f"https://api.ebird.org/v2/product/checklist/view/{subId}"
#         payload={}
#         headers = {
#             'X-eBirdApiToken': self.token
#         }
#         response = requests.request("GET", url, headers=headers, data=payload)
#         res = response.text
#         return json.loads(res)

#     # detail = get_report_detail(token=token, subId='S148184150')
#     # taxons = detail['obs']
#     # for taxon in taxons:
#     #     print(detail["subId"],
#     #         detail["locId"],
#     #         taxon["speciesCode"],
#     #         taxon["howManyStr"])

#     # res = get_historic_obs(date='2023/8/27')
#     # # res = get_recent_obs()
#     # # # print(json.dumps(res,sort_keys=True, indent=4, separators=(',', ': ')))
#     # for _list in res:
#     #     try:
#     #         if "howMany" in _list:
#     #             howMany = _list["howMany"]
#     #         else:
#     #             howMany = 'X'
#     #         # print(_list)
#     #         print(_list["subId"],
#     #             _list["speciesCode"],
#     #             _list["comName"],
#     #             howMany,
#     #             _list["lat"],
#     #             _list["lng"],
#     #             _list["locName"]
#     #             )
#     #     except Exception as e:
#     #         print(f"{_list} error")
#     #         print(e)


#     # def get_all_report_url_list():
#     #     pass

#     # res = get_recent_obs()
#     # print(json.dumps(res,sort_keys=True, indent=4, separators=(',', ': ')))
#     # print(json.dumps(res,sort_keys=True, indent=4, separators=(',', ': ')))

#     def get_back_date(self, n):
#         t = int(time.time()) - n*60*60*24
#         ta = time.localtime(t)
#         return time.strftime("%Y/%m/%d", ta)

#     def date_to_ta(self, date):
#         return int(time.mktime(time.strptime(date,"%Y/%m/%d")))

#     def ta_to_date(self, ta):
#         return time.strftime("%Y/%m/%d", time.localtime(ta))

#     def search(self, taxonid='', startTime='', endTime='', province='', city='', district='', pointname='', username='', serial_id='', ctime='', taxonname='', state=''):
#         id_list = []
#         id_detail = {}

#         ta_s = self.date_to_ta(startTime)
#         ta_e = self.date_to_ta(endTime)
#         # print(ta_s, ta_e)
#         back = int((ta_e - ta_s) / 86400)
#         # print(back)
#         date_list = [self.ta_to_date(ta_s+86400*i) for i in range(back+1)]
#         print('查询日期\n',date_list)

#         print('正在获取日期范围内的checklist id...')

#         lock1 = threading.Lock()
#         def loop1():
#             while len(date_list):
#                 lock1.acquire()
#                 _date =  date_list.pop()
#                 lock1.release()
#                 res = self.get_historic_list(date=_date)
#                 # print(json.dumps(res,sort_keys=True, indent=4, separators=(',', ': ')))
#                 print('thread %s >>> %s' % (threading.current_thread().name, _date))
#                 for item in res:
#                     try:
#                         id_detail[item["subId"]] = item
#                         # {
#                             # 'lat':item["loc"]["lat"],
#                             # 'lng':item["loc"]["lng"],
#                             # 'locName':item["loc"]["locName"],
#                             # 'userDisplayName':item["userDisplayName"]
#                         # }
#                         id_list.append(item["subId"])
#                     except Exception as e:
#                         print(f"{item} error")
#                         print(e)

#         t1 = []
#         for i in range(multiprocessing.cpu_count()):
#             t1.append(threading.Thread(target=loop1))
#             t1[i].start()
#         for i in range(multiprocessing.cpu_count()):
#             t1[i].join()

#         print(id_list)
#         checklists = []
#         print(f'共计{len(id_list)}份报告')

#         lock2 = threading.Lock()
#         def loop2():
#             while len(id_list):
#                 lock2.acquire()
#                 _id =  id_list.pop()
#                 lock2.release()
#             # for _id in id_list:
#                 detail = self.get_report_detail(subId=_id)
#                 # detail["lat"] = id_detail[_id]["lat"]
#                 # detail["lng"] = id_detail[_id]["lng"]
#                 # detail["locName"] = id_detail[_id]["locName"]
#                 # detail["userDisplayName"] = id_detail[_id]["userDisplayName"]
#                 print('thread %s >>> %s' % (threading.current_thread().name, _id))
#                 for _ in id_detail[_id]:
#                     if _ not in detail:
#                         detail[_] = id_detail[_id][_]
#                 # print(json.dumps(id_detail[_id],sort_keys=True, indent=4, separators=(',', ': ')))
#                 # print(json.dumps(detail,sort_keys=True, indent=4, separators=(',', ': ')))
#                 checklists.append(detail)

#         t2 = []
#         for i in range(multiprocessing.cpu_count()):
#             t2.append(threading.Thread(target=loop2))
#             t2[i].start()
#         for i in range(multiprocessing.cpu_count()):
#             t2[i].join()

#         print(f'已获取{len(checklists)}份报告')
#         return checklists
#             # taxons = detail['obs']
#             # for taxon in taxons:
#             #     print(detail["subId"],
#             #         detail["obsDt"],
#             #         id_detail[_id]["lat"],
#             #         id_detail[_id]["lng"],
#             #         id_detail[_id]["locName"],
#             #         taxon["speciesCode"],
#             #         taxon["howManyStr"])
#     def show(self, checklists):
#         for item in checklists:
#             loc = item['loc']
#             obs = item['obs']
#             print(loc['lat'], loc['lng'], loc['locName'])
#             for taxon in obs:
#                 speciesCode = taxon['speciesCode']
#                 # # debug
#                 # if speciesCode == 'litgre3':
#                 #     print(json.dumps(taxon,sort_keys=True, indent=4, separators=(',', ': ')))
#                 #     input('wait')
#                 sciName = self.get_sciName_from_speciesCode(speciesCode)
#                 comName = self.get_comName_from_sciName(sciName)
#                 howManyStr = taxon["howManyStr"]
#                 print(speciesCode, sciName, comName, howManyStr)
#     def spp_info(self, checklists):
#         info = {}
#         for item in checklists:
#             loc = item['loc']
#             obs = item['obs']
#             obsDt = item['obsDt']
#             # .split(' ')[0]
#             for taxon in obs:
#                 speciesCode = taxon['speciesCode']
#                 # print(json.dumps(taxon,sort_keys=True, indent=4, separators=(',', ': ')))
#                 # input('wait...')
#                 sciName = self.get_sciName_from_speciesCode(speciesCode)
#                 comName = self.get_comName_from_sciName(sciName)
#                 howManyStr = taxon["howManyStr"]
#                 if comName not in info:
#                     info[comName] = []
#                 info[comName].append((obsDt, howManyStr, loc['lat'], loc['lng'], loc['locName'],0))
#         return info
