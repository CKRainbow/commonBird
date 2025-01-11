# Not needed?
# -*- coding: utf-8 -*- for popen for windows
from functools import partial
import subprocess

subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")
##############################################

import multiprocessing
import hashlib
import json
import asyncio
import urllib
import time
import os
import logging
from typing import Callable
from pathlib import Path

import execjs
import httpx
from dotenv import load_dotenv

from .. import inner_path


class Birdreport:
    def __init__(self, token: str):
        # TODO: python-based js executor like
        with open(Path(inner_path) / "jQuertAjax.js", "r", encoding="utf-8") as f:
            node_path = Path(inner_path) / "node_modules"
            self.ctx = execjs.compile(f.read(), cwd=node_path)
        self.token = token
        self.user_info = None

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
        return self.ctx.call("getTimestamp")

    def getRequestId(self):
        return self.ctx.call("getUuid")

    def encrypt(self, text):
        return self.ctx.call("encrypt", text)

    def decrypt(self, text):
        return self.ctx.call("decode", text)

    def format(self, text):
        return self.ctx.call("format", text)

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

    def get_crypt_request_info(self, _data):
        format_data = self.format(_data)
        encrypt_data = self.encrypt(format_data)
        timestamp = self.getTimestamp()
        request_id = self.getRequestId()
        concat = format_data + request_id + str(timestamp)
        sign = self.md5(concat)
        headers = self.get_crypt_headers(request_id, timestamp, sign)
        return headers, encrypt_data

    def get_request_info(self, _data):
        format_data = json.dumps(_data)
        headers = self.get_headers()
        return headers, format_data

    def get_activity_detail(self, aid):
        params = {
            "reportId": aid,
        }
        a = self.get_data(
            urllib.parse.urlencode(params),
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

    async def member_get_taxon_list(self):
        params = {}

        result = await self.get_data(
            params,
            "https://api.birdreport.cn/member/system/taxon/list",
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
            urllib.parse.urlencode(params),
            "https://api.birdreport.cn/front/activity/taxon",
        )

    def search_hotspots_by_name(self, name: str):
        params = {
            "limit": 100,
            "keywords": name,
            "t": self.getTimestamp(),
        }
        # format_params = urllib.parse.urlencode(params)
        format_params = params
        return self.get_data(
            format_params,
            "https://api.birdreport.cn/member/system/point/hots",
            encode=False,
            decode=False,
        )

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
            urllib.parse.urlencode(params),
            "https://api.birdreport.cn/front/record/activity/search",
        )
        return a

    async def get_data(self, param, url, encode=True, decode=True):
        if encode:
            headers, format_param = self.get_crypt_request_info(param)
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

        reports = await self.get_all_report_url_list(
            params, self.member_search, limit=200
        )
        if len(reports) == 0:
            return []
        checklists = {
            report["id"]: report for report in reports if report["is_convert"] == 0
        }
        ids = list(checklists.keys())
        excel_data = await self.member_get_excel(ids)
        for taxon_entry in excel_data:
            checklist = checklists[taxon_entry["activity_id"]]
            if "obs" not in checklist:
                checklist["obs"] = []
            checklist["obs"].append(taxon_entry)

        return list(checklists.values())

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

    def show(self, checklists):
        for item in checklists:
            lng, lat = item["location"].split(",")
            print(lat, lng, item["point_name"])
            obs = item["obs"]
            for taxon in obs:
                sciName = taxon["latinname"]
                comName = taxon["taxon_name"]
                howManyStr = taxon["taxon_count"]
                print(sciName, comName, howManyStr)

    def spp_info(self, checklists):
        info = {}
        for item in checklists:
            # lng, lat = item["location"].split(",")
            obs = item["obs"]
            obsDt = item["start_time"]
            for taxon in obs:
                sciName = taxon["latinname"]
                comName = taxon["taxon_name"]
                howManyStr = taxon["taxon_count"]
                if comName not in info:
                    info[comName] = []
                info[comName].append(
                    # (obsDt, howManyStr, lat, lng, item["point_name"], 1)
                    (obsDt, howManyStr, item["point_name"], 1)
                )
        return info


if __name__ == "__main__":
    load_dotenv()
    y = Birdreport(os.getenv("BIRDREPORT_TOKEN"))

    async def test():
        # result = await asyncio.create_task(y.member_get_taxon_detail(1142574))
        # result = await asyncio.create_task(y.member_get_taxon_list())
        # with open("bird_report_taxon_list.json", "w", encoding="utf-8") as f:
        #     json.dump(result, f, ensure_ascii=False, indent=2)
        pass

    asyncio.run(test())
    # asyncio.run(test())
    # data = y.search(
    #     username="ckrainbow", mode=1, start_date="2025-01-01", end_date="2025-01-02"
    # )
    # data = y.member_get_activity_detail(1121437)
    # data = y.search_hotspots_by_name("上海科技")
    # data = y.get_activity_detail("7445f741-a468-469d-93ac-39779c92770b")
    # print(data)
