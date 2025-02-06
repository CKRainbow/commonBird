import multiprocessing
import hashlib
import json
import asyncio
import subprocess
import time
import os
import logging
import uuid
import sys
import base64
from typing import Callable

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from dotenv import load_dotenv

from src import inner_path, MyPopen
from src.utils.consts import BirdreportTaxonVersion

subprocess.Popen = MyPopen

import execjs


class Birdreport:
    def __init__(self, token: str):
        # TODO: python-based js executor like
        if getattr(sys, "frozen", False):
            runtime = execjs.get("local_node")
        else:
            runtime = execjs.get()
        with open(inner_path / "jQuertAjax.js", "r", encoding="utf-8") as f:
            node_path = inner_path / "node_modules"
            self.ctx = runtime.compile(f.read(), cwd=node_path)
        self.token = token
        self.user_info = None

        self.cipher = AES.new(
            b"C8EB5514AF5ADDB94B2207B08C66601C", AES.MODE_CBC, iv=b"55DD79C6F04E1A67"
        )

    @classmethod
    async def create(cls, token: str):
        instance = cls(token)
        user_info = await instance.member_get_user()
        instance.user_info = user_info
        return instance

    def get_back_date(self, n):
        t = int(time.time()) - n * 60 * 60 * 24
        # ta_now = time.localtime(now)
        ta = time.localtime(t)
        return time.strftime("%Y-%m-%d", ta)

    def md5(self, text):
        hl = hashlib.md5()
        hl.update(text.encode(encoding="utf-8"))
        return hl.hexdigest()

    def getTimestamp(self):
        return str(int(time.time())) + "000"

    def getRequestId(self):
        return uuid.uuid4().hex

    def encrypt(self, text):
        return self.ctx.call("encrypt", text)

    def encrypt_batch(self, texts):
        return self.ctx.call("encryptBatch", texts)

    def decrypt(self, text):
        text = base64.b64decode(text)
        return unpad(self.cipher.decrypt(text), AES.block_size).decode("utf-8")

    def format(self, data):
        return json.dumps(data).replace(" ", "")

    def get_headers(self):
        # sign = md5(format_param + request_id + str(timestamp))
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,ja;q=0.7,es;q=0.6,es-ES;q=0.5",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Host": "api.birdreport.cn",
            "Origin": "https://www.birdreport.cn",
            "Referer": "https://www.birdreport.cn/",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

        if self.token is not None and self.token != "":
            headers["X-Auth-Token"] = self.token

        return headers

    def get_crypt_headers(self, request_id, timestamp, sign):
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,ja;q=0.7,es;q=0.6,es-ES;q=0.5",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "api.birdreport.cn",
            "Origin": "https://www.birdreport.cn",
            "Referer": "https://www.birdreport.cn/",
            "requestId": request_id,
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "sign": sign,
            "timestamp": str(timestamp),
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        if self.token is not None and self.token != "":
            headers["X-Auth-Token"] = self.token

        return headers

    async def get_crypt_request_info(self, _data):
        await asyncio.sleep(0.01)
        format_data = self.format(_data)
        encrypt_data = self.encrypt(format_data)  # time consuming
        timestamp = self.getTimestamp()
        request_id = self.getRequestId()
        concat = format_data + request_id + str(timestamp)
        sign = self.md5(concat)
        headers = self.get_crypt_headers(request_id, timestamp, sign)
        return headers, encrypt_data

    def get_request_info(self, _data):
        format_data = self.format(_data)
        headers = self.get_headers()
        return headers, format_data

    def get_activity_detail(self, aid):
        params = {
            "reportId": aid,
        }
        a = self.get_data(
            params,
            "https://api.birdreport.cn/front/activity/get",
        )
        return a

    async def member_get_activity_detail(self, serial_id):
        params = {
            "id": str(serial_id),
        }

        return await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/activity/get",
            encode=False,
            decode=False,
        )

    async def member_get_taxon_stat(self, serial_id):
        params = {
            "activity_id": str(serial_id),
        }

        return await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/record/groupTaxon",
            encode=False,
        )

    async def member_get_taxon_detail(self, serial_id):
        params = {
            "activity_id": str(serial_id),
        }

        return await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/record/search",
            encode=False,
        )

    async def member_get_user(self):
        params = {}

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/user/get",
            encode=False,
            decode=False,
        )

        return result["data"]

    async def member_get_excel(self, ids):
        params = {"ids": ",".join([str(id) for id in ids])}

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/record/excel",
            encode=False,
            decode=False,
        )

        return result["data"]

    async def member_handy_get_excel(self, ids):
        params = {"ids": ",".join([str(id) for id in ids])}

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/handy/record/excel",
            encode=False,
            decode=False,
        )

        return result["data"]

    async def member_get_taxon_list(self):
        params = {}

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/taxon/list",
            encode=False,
            decode=False,
        )

        return result["data"]

    async def get_taxon_infos_by_version(self, version: BirdreportTaxonVersion):
        params = {
            "version": version.value,
        }

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/front/excel/selectTaxon",
            encode=False,
            decode=False,
        )

        return result["data"]

    def get_taxon(self, aid):
        params = {
            "reportId": aid,
            "page": "1",
            "limit": "1500",
        }
        return self.get_data(
            params,
            "https://api.birdreport.cn/front/activity/taxon",
        )

    async def member_search_hotspots_by_name(self, name: str):
        params = {
            "limit": 100,
            "keywords": name,
            "t": self.getTimestamp(),
        }

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/point/hots",
            encode=False,
            decode=False,
        )

        return result["data"]

    async def member_search_hotspots_nearby(
        self, distance: int, latitude: float, longitude: float, limit: int = 20
    ):
        params = {
            "distance": f"{distance}",
            "latitude": f"{latitude}",
            "longitude": f"{longitude}",
            "limit": f"{limit}",
        }

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/point/nearby",
            encode=False,
            decode=False,
        )

        return result["data"]

    def get_report_url_list(self, page, limit, data):
        # format_params = f"page={page}&limit={limit}&taxonid=&startTime=&endTime=&province=&city=&district=&pointname=&username=&serial_id=&ctime=&taxonname=&state=&mode=0&outside_type=0"
        params = {
            "page": f"{page}",
            "limit": f"{limit}",  # 似乎不允许设置于预设不同的值
            "taxonid": f"{data['taxonid']}",  # 逗号分隔
            "startTime": f"{data['startTime']}",
            "endTime": f"{data['endTime']}",
            "province": f"{data['province']}",
            "city": f"{data['city']}",
            "district": f"{data['district']}",
            "pointname": f"{data['pointname']}",
            "username": f"{data['username']}",
            "serial_id": f"{data['serial_id']}",  # 记录编号
            "ctime": f"{data['ctime']}",  # 精确日期
            "state": f"{data['state']}",  # 2 公开 1,3 私密
            "mode": f"{data['mode']}",  # 0:模糊搜索 1:精确搜索
            "outside_type": "",  # 是否为标红报告
        }

        a = self.get_data(
            params,
            "https://api.birdreport.cn/front/record/activity/search",
        )
        return a

    async def get_data(self, param, url, encode=True, decode=True):
        if encode:
            headers, format_param = await self.get_crypt_request_info(param)
        else:
            headers, format_param = self.get_request_info(param)

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=format_param)
        if decode:
            encrypt_res = response.json()
            _data = json.loads(self.decrypt(encrypt_res["data"]))
        else:
            _data = response.json()
        return _data

    async def get_all_report_url_list(self, data, report_api: Callable, limit=50):
        page = 1
        limit = limit
        _data_list = []
        while 1:
            try:
                report_list = await report_api(page, limit, **data)
                for report in report_list:
                    _data_list.append(report)
                print(f"获取第{page}页")
            except Exception as e:
                print(e)
                continue
            if len(report_list) == 0:
                break
            if len(report_list) < limit:
                break
            page += 1
        print(f"正在获取{len(_data_list)}份报告")
        return _data_list

    async def member_get_reports(
        self,
        start_date="",
        end_date="",
        point_name="",
        serial_id="",
        state="",
        taxon_id="",
    ):
        params = {
            "start_date": f"{start_date}",
            "end_date": f"{end_date}",
            "point_name": f"{point_name}",
            "serial_id": f"{serial_id}",
            "state": f"{state}",
            "taxon_id": f"{taxon_id}",
        }
        checklists = {}
        point_reports = await self.get_all_report_url_list(
            params, self.member_search, limit=200
        )
        if len(point_reports) != 0:
            point_checklists = {report["id"]: report for report in point_reports}
            ids = list(point_checklists.keys())
            point_excel_data = await self.member_get_excel(ids)
            for taxon_entry in point_excel_data:
                checklist = point_checklists[taxon_entry["activity_id"]]
                if "obs" not in checklist:
                    checklist["obs"] = []
                checklist["obs"].append(taxon_entry)
            checklists.update(point_checklists)

        params = {
            "start_date": f"{start_date}",
            "end_date": f"{end_date}",
            "serial_id": f"{serial_id}",
            "taxon_id": f"{taxon_id}",
        }
        handy_reports = await self.get_all_report_url_list(
            params, self.member_handy_search, limit=200
        )
        if len(handy_reports) != 0:
            handy_checklists = {report["id"]: report for report in handy_reports}
            ids = list(handy_checklists.keys())
            handy_excel_data = await self.member_handy_get_excel(ids)
            for taxon_entry in handy_excel_data:
                checklist = handy_checklists[taxon_entry["activity_id"]]
                if "obs" not in checklist:
                    checklist["obs"] = []
                checklist["obs"].append(taxon_entry)
            # use the lat, long and city district as those of the report
            # and assign a psudo-point_name
            for checklist in handy_checklists.values():
                first_record = checklist["obs"][0]
                checklist["city_name"] = first_record["city_name"]
                checklist["district_name"] = first_record["district_name"]
                checklist["latitude"] = first_record["latitude"]
                checklist["longitude"] = first_record["longitude"]
                checklist["point_name"] = f"随手记地点-{checklist['start_time']}"
            checklists.update(handy_checklists)

        return list(checklists.values())

    async def member_handy_search(
        self, page, limit, start_date="", end_date="", serial_id="", taxon_id=""
    ):
        params = {
            "start_date": f"{start_date}",
            "start": f"{start_date}",
            "end_date": f"{end_date}",
            "end": f"{end_date}",
            "serial_id": f"{serial_id}",
            "taxon_id": f"{taxon_id}",
            "page": f"{page}",
            "limit": f"{limit}",
        }
        print(params)

        res = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/handy/report/search",
            encode=False,
            decode=True,
        )
        return res

    async def member_search(
        self,
        page,
        limit,
        start_date="",
        end_date="",
        point_name="",
        serial_id="",
        state="",
        taxon_id="",
    ):
        params = {
            "start_date": f"{start_date}",
            "start": f"{start_date}",
            "end_date": f"{end_date}",
            "end": f"{end_date}",
            "point_name": f"{point_name}",
            "serial_id": f"{serial_id}",
            "state": f"{state}",
            "taxon_id": f"{taxon_id}",
            "page": f"{page}",
            "limit": f"{limit}",
        }

        res = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/activity/search",
            encode=False,
            decode=True,
        )
        return res

    async def get_taxon_from_reports(self, reports):
        if len(reports) <= 0:
            return []
        is_member = "id" in reports[0]

        id_detail = {}

        for item in reports:
            if is_member:
                id = item["id"]
            else:
                id = item["reportId"]
            id_detail[id] = item

        async def get_detail_and_taxon(self, report, id):
            if is_member:
                detail = await self.member_get_activity_detail(id)
                taxons = await self.member_get_taxon_stat(id)
                print(f"已获取报告[{id}]")
                report["obs"] = taxons
                for key, value in detail["data"].items():
                    if value is None:
                        continue
                    report[key] = value
            else:
                detail = await self.get_activity_detail(id)
                taxons = await self.get_taxon(id)
                print(f"已获取报告[{id}]")
                report["obs"] = taxons
                for key, value in detail.items():
                    if value is None:
                        continue
                    report[key] = value

        # get cpu number
        cpu_count = multiprocessing.cpu_count()
        batch_size = cpu_count // 2

        id_detail_items = list(id_detail.items())
        for i in range(0, len(id_detail), batch_size):
            tasks = [
                get_detail_and_taxon(self, report, id)
                for id, report in id_detail_items[i : i + batch_size]
            ]
            await asyncio.gather(*tasks)

        print(f"已获取{len(id_detail)}份报告")

        return list(id_detail.values())

    def search(
        self,
        taxonid="",
        start_date="",
        end_date="",
        province="",
        city="",
        district="",
        pointname="",
        username="",
        serial_id="",
        ctime="",
        taxonname="",
        state="",
        mode="",
    ):
        data = {
            "taxonid": f"{taxonid}",
            "startTime": f"{start_date}",
            "endTime": f"{end_date}",
            "province": f"{province}",
            "city": f"{city}",
            "district": f"{district}",
            "pointname": f"{pointname}",
            "username": f"{username}",
            "serial_id": f"{serial_id}",
            "ctime": f"{ctime}",
            "taxonname": f"{taxonname}",
            "state": f"{state}",
            "mode": f"{mode}",
        }

        res = self.get_all_report_url_list(data, self.get_report_url_list)
        checklists = self.get_taxon_from_reports(res)

        return checklists

    async def get_taxon_info(self, id: int):
        params = {
            "id": f"{id}",
        }

        res = await self.get_data(
            params,
            "https://api.birdreport.cn/front/taxon/get",
            encode=True,
            decode=False,
        )
        return res["data"]

    # async def get_taxon_info_batch(self, ids: List[int]):
    #     async def gd(headers, data):
    #         async with httpx.AsyncClient() as client:
    #             response = await client.post(
    #                 "https://api.birdreport.cn/front/taxon/get",
    #                 headers=headers,
    #                 data=data,
    #             )
    #         _data = response.json()
    #         print(_data)
    #         return _data["data"]

    #     format_datas = [json.dumps({"id": f"{id}"}).replace(" ", "") for id in ids]
    #     print(format_datas)

    #     encrypt_datas = self.encrypt_batch(format_datas)
    #     print(encrypt_datas)

    #     tasks = []
    #     for encrypt_data in encrypt_datas:
    #         timestamp = self.getTimestamp()
    #         request_id = self.getRequestId()
    #         concat = encrypt_data + request_id + str(timestamp)
    #         sign = self.md5(concat)
    #         headers = self.get_crypt_headers(request_id, timestamp, sign)

    #         tasks.append(gd(headers, encrypt_data))

    #     res = await asyncio.gather(*tasks)
    #     print(res)

    #     return res


if __name__ == "__main__":
    load_dotenv()
    y = Birdreport(os.getenv("BIRDREPORT_TOKEN"))

    # re = y.decrypt(
    #     "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"
    # )

    # print(re)

    async def test():
        # result = await asyncio.create_task(y.member_get_taxon_detail(1142574))
        # result = await asyncio.create_task(y.member_get_taxon_list())
        # with open("bird_report_taxon_list.json", "w", encoding="utf-8") as f:
        #     json.dump(result, f, ensure_ascii=False, indent=2)
        result = await y.get_taxon_info(1)
        print(result)

    asyncio.run(test())
    # asyncio.run(test())
    # data = y.search(
    #     username="ckrainbow", mode=1, start_date="2025-01-01", end_date="2025-01-02"
    # )
    # data = y.member_get_activity_detail(1121437)
    # data = y.search_hotspots_by_name("上海科技")
    # data = y.get_activity_detail("7445f741-a468-469d-93ac-39779c92770b")
    # print(data)
