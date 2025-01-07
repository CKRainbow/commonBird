# -*- coding: utf-8 -*- for popen for windows
from functools import partial
import subprocess

subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")

import hashlib
import json

import execjs
import pandas as pd
import requests

import urllib
import time
import sys

import threading
import multiprocessing


class Birdreport:
    def __init__(self, token: str):
        with open("./jQuertAjax.js", "r", encoding="utf-8") as f:
            node_path = "./node_modules"
            self.ctx = execjs.compile(f.read(), cwd=node_path)
        self.token = token

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

    def get_headers(self, auth_token=None):
        # sign = md5(format_param + request_id + str(timestamp))
        auth_token = "A227EBF843724E89A847B23F815D10CA"

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,ja;q=0.7,es;q=0.6,es-ES;q=0.5",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Host": "api.birdreport.cn",
            "Origin": "https://www.birdreport.cn",
            "Referer": "https://www.birdreport.cn/",
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

        if auth_token is not None:
            headers["X-Auth-Token"] = auth_token

        return headers

    def get_crypt_headers(self, request_id, timestamp, sign, auth_token=None):
        # sign = md5(format_param + request_id + str(timestamp))
        auth_token = "A227EBF843724E89A847B23F815D10CA"

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en,zh-CN;q=0.9,zh;q=0.8,ja;q=0.7,es;q=0.6,es-ES;q=0.5",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "api.birdreport.cn",
            "Origin": "https://www.birdreport.cn",
            "Referer": "https://www.birdreport.cn/",
            "requestId": request_id,
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "sign": sign,
            "timestamp": str(timestamp),
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        }

        if auth_token is not None:
            headers["X-Auth-Token"] = auth_token

        return headers

    def get_crypt_request_info(self, _data):
        format_data = self.format(_data)
        encrypt_data = self.encrypt(format_data)
        timestamp = self.getTimestamp()
        request_id = self.getRequestId()
        concat = format_data + request_id + str(timestamp)
        sign = self.md5(concat)
        headers = self.get_crypt_headers(request_id, timestamp, sign)
        print(format_data)
        print(sign)
        print(encrypt_data)
        return headers, encrypt_data

    def get_request_info(self, _data):
        format_data = json.dumps(_data)
        headers = self.get_headers()
        print(format_data)
        return headers, format_data

    def get_report_detail(self, aid):
        format_params = f"activityid={str(aid)}"
        a = self.get_decrypted_data(
            format_params, "https://api.birdreport.cn/front/activity/get"
        )
        return a

    def get_taxon(self, aid):
        format_params = f"page=1&limit=1500&reportId={aid}"
        return self.get_decrypted_data(
            format_params,
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
            format_params, "https://api.birdreport.cn/member/system/point/hots"
        )

    def get_report_url_list(self, page, limit, data):
        # format_params = f"page={page}&limit={limit}&taxonid=&startTime=&endTime=&province=&city=&district=&pointname=&username=&serial_id=&ctime=&taxonname=&state=&mode=0&outside_type=0"
        params = {
            "page": f"{page}",
            "limit": f"{limit}",
            "taxonid": f"{data['taxonid']}",
            "startTime": f"{data['startTime']}",
            "endTime": f"{data['endTime']}",
            "province": f"{data['province']}",
            "city": f"{data['city']}",
            "district": f"{data['district']}",
            "pointname": f"{data['pointname']}",
            "username": f"{data['username']}",
            "serial_id": f"{data['serial_id']}",
            "ctime": f"{data['ctime']}",
            "state": f"{data['state']}",
            "mode": "0",
            "outside_type": "0",
        }
        print(params)

        # format_params = f"page={page}&limit={limit}&taxonid=&startTime={start}&endTime={end}&province=%E5%8C%97%E4%BA%AC%E5%B8%82&city=%E5%8C%97%E4%BA%AC%E5%B8%82&district=&pointname=&username=&serial_id=&ctime=&taxonname=&state=2&mode=0&outside_type=0"
        a = self.get_decrypted_data(
            urllib.parse.urlencode(params),
            "https://api.birdreport.cn/front/record/activity/search",
        )
        return a

    def get_decrypted_data(self, format_param, url):
        # 构造请求头，和请求参数加密
        headers, encrypt_data = self.get_crypt_request_info(format_param)

        response = requests.post(url, headers=headers, data=encrypt_data)
        encrypt_res = response.json()
        print(encrypt_res)
        # 解密数据
        _data = self.decrypt(encrypt_res["data"])
        return json.loads(_data)

    def get_data(self, param, url):
        headers, format_param = self.get_request_info(param)

        response = requests.post(url, headers=headers, data=format_param)
        return response.json()

    def get_all_report_url_list(self, data):
        _data_list = []
        page = 1
        limit = 50
        _data_list = []
        while 1:
            try:
                report_list = self.get_report_url_list(page, limit, data)
                print(report_list)
                for report in report_list:
                    if report["state"] == 1:
                        continue
                    _data_list.append(report)
                print(f"获取第{page}页")
            except Exception as e:
                continue
            if len(report_list) == 0:
                break
            if len(report_list) < limit:
                break
            page += 1
        print(f"正在获取{len(_data_list)}份报告")
        # with open("aid.txt", "w+", encoding="utf-8") as _f:
        #     for _item in _data_list:
        #         _f.write(json.dumps(_item))
        #         _f.write("\n")
        return _data_list

    def search(
        self,
        taxonid="",
        startTime="",
        endTime="",
        province="",
        city="",
        district="",
        pointname="",
        username="",
        serial_id="",
        ctime="",
        taxonname="",
        state="",
    ):
        # df = {"位置": [], "坐标": [], "名称": [], "数量": []}

        data = {
            "taxonid": f"{taxonid}",
            "startTime": f"{startTime}",
            "endTime": f"{endTime}",
            "province": f"{province}",
            "city": f"{city}",
            "district": f"{district}",
            "pointname": f"{pointname}",
            "username": f"{username}",
            "serial_id": f"{serial_id}",
            "ctime": f"{ctime}",
            "taxonname": f"{taxonname}",
            "state": f"{state}",
        }

        res = self.get_all_report_url_list(data)
        id_list = []
        id_detail = {}

        checklists = []
        for item in res:
            id_detail[item["reportId"]] = item
            id_list.append(item["reportId"])

        print(id_list)

        lock = threading.Lock()

        # get obs in checklist
        def loop():
            while len(id_list):
                lock.acquire()
                _id = id_list.pop()
                lock.release()

                # detail = self.get_report_detail(_id)
                detail = id_detail[_id]
                print("thread %s >>> %s" % (threading.current_thread().name, _id))
                # print('detail',detail)
                taxons = self.get_taxon(_id)
                print(taxons)
                # print(json.dumps(taxons,sort_keys=True, indent=4, separators=(',', ': ')))
                # print('taxons',taxons)
                detail["obs"] = taxons
                checklists.append(detail)
                # print(json.dumps(detail,sort_keys=True, indent=4, separators=(',', ': ')))

        t = []
        for i in range(multiprocessing.cpu_count()):
            t.append(threading.Thread(target=loop))
            t[i].start()
        for i in range(multiprocessing.cpu_count()):
            t[i].join()

        print(f"已获取{len(checklists)}份报告")

        return checklists
        # data_frame = pd.DataFrame(df)
        # data_frame.to_excel("info.xlsx", index=False)

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
    y = Birdreport()
    data = y.get_taxon("194c4e0-be24-4564-b778-9ab96eed1341")
    print(data)
