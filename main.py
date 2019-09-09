import copy
import json
import math
import os
import re
import time
from parser import parser_select
from pprint import pprint
from random import choice
from urllib.parse import urljoin
from dataclasses import dataclass

import asks
import click
import pandas
import requests
import trio
import pathlib
from pyquery import PyQuery as jq
from retry import retry
from termcolor import colored

from common import addfailed, addsucess, check_path, check_times, init_path
from conf import config
from exporter import create_json, create_xlsx
from log import error, info, makeStatus, success, warning
from task import save_to_mongo

# import pudb; pudb.set_trace()

asks.init("trio")


@dataclass()
class LIANJIA(object):
    ua_list = pathlib.Path(config.ua_file).open("r").readlines()
    results = {}
    reg_list = {"citys": re.compile('cityList":(.*?)\},f')}
    url_list_maps = {
        "old": "二手房",
        "new": "新房",
        "chuzu": "出租房",
        "xiaoqu": "小区",
        "zhuangxiu": "装修",
    }

    current_city = ""
    current_type = ""
    current_url = ""

    domain = "m.lianjia.com"
    page_length = 30
    max_page = 2

    city_names = f"{config.datas_file}/citys.json"
    menu_session = requests.Session()
    limit = trio.CapacityLimiter(config.max_connections)

    async def ready(self):
        self.menu_session.headers = config.fake_header
        self.menu_session.headers.update({"User-Agent": self.random_ua()})
        self.async_session = asks.Session(connections=config.max_connections)
        self.async_session.headers = config.fake_header
        self.main_url = f"https://{self.domain}/"
        self.url_list = {
            "citys": urljoin(self.main_url, "city/"),
            "old": lambda page: urljoin(
                self.main_url, f"/{self.current_city}/ershoufang/pg{page}/?_t=1"
            ),
            "new": lambda page: urljoin(
                self.main_url,
                f"/{self.current_city}/loupan/pg{page}/?_t=1&source=index",
            ),
            "chuzu": lambda page: urljoin(
                self.main_url, f"/chuzu/{self.current_city}/zufang/pg{page}/?ajax=1"
            ),
            "xiaoqu": lambda page: urljoin(
                self.main_url, f"/{self.current_city}/xiaoqu/pg{page}/?_t=1"
            ),
            "zhuangxiu": lambda page: urljoin(
                self.main_url,
                f"/home/{self.current_city}/zhuangxiu/list/getCompanyInfoList?tagID=&page={page}&pageSize=10&timer={int(time.time())}",
            ),
        }
        list(map(init_path, [config.debug_file, config.datas_file]))

    def reset(self):
        self.results = {}
        self.current_city = ""
        self.current_url = ""
        config.status = copy.deepcopy(config.default_status)

    def random_ua(self):
        return choice(self.ua_list).strip()

    def save_debug_file(self, text, name):
        with pathlib.Path(f"{config.debug_file}/{name}").open("w") as f:
            f.write(text)

    async def aiosave_debug_file(self, text, name):
        async with await trio.open_file(f"{config.debug_file}/{name}", "w") as f:
            await f.write(text)

    async def get_single(self, page=1):
        url = self.current_url(page)
        warning(f"[{page}]请求: {url}")
        try:
            resp = await self.async_session.get(
                url,
                headers={"User-Agent": self.random_ua()}
                if self.current_type in ["chuzu"] and page == 1
                else {
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "DNT": "1",
                    "Host": "m.lianjia.com",
                    "Pragma": "no-cache",
                    "Referer": f"https://m.lianjia.com/jian/ershoufang/pg{choice([1,10,100])}/",
                    "User-Agent": self.random_ua(),
                    "X-Requested-With": "XMLHttpRequest",
                    # "X-Tingyun-Id": "gVpxXPG41PA;r=425877255"
                },
            )
            assert resp.status_code == 200

            max_nums = 0
            html = ""
            success(f"[{page}]响应: {url}")
            jsondatas = None

            if self.current_type not in ["chuzu"] or (
                self.current_type in ["chuzu"] and page > 1
            ):
                jsondatas = resp.json()

            if self.current_type == "old":
                max_nums = json.loads(jsondatas["args"])["total"]
                html = jsondatas["body"]

            elif self.current_type == "new":
                max_nums = int(jsondatas["data"]["total"])
                html = jsondatas["data"]["body"]

            if page == 1:

                if self.current_type == "chuzu":
                    max_nums = int(
                        jq(resp.text)('input[data-el="digItemCount"]').attr(
                            "data-item-count"
                        )
                    )
                    html = resp.text
                self.max_page = math.ceil(max_nums / self.page_length)
                success(f"数量: {max_nums} 页数: {self.max_page}")
                await trio.sleep(10)
            else:
                if self.current_type == "chuzu":
                    html = jsondatas["body"]
            addsucess()
            self.results.update(
                parser_select(html, resp.url, self.current_type, self.current_city)
            )
        except Exception as e:
            error(f"{url} {e}")
            addfailed()
            raise e

    async def get_detail(self, hid, url):
        async with self.limit:
            warning(f"请求: {url}")
            try:
                resp = await self.async_session.get(url)
                success(f"响应: {url}")
                new_details = parser_select(
                    resp.text,
                    resp.url,
                    f"{self.current_type}_details",
                    self.current_city,
                )
                info(new_details)
                self.results[hid].update(new_details)
                save_to_mongo.delay(self.results[hid], self.current_type)
            except Exception as e:
                error(f"{url} {e}")

    async def get_all(self):
        await self.get_single()
        if not config.run_for_test:
            async with trio.open_nursery() as nursery:
                for page in range(2, self.max_page):
                    nursery.start_soon(self.get_single, page)

    async def add_detail(self):
        """
            添加详情
        """
        async with trio.open_nursery() as nursery:
            for tid, item in self.results.items():
                nursery.start_soon(self.get_detail, tid, item["url"])

    def get_city(self):
        """
            获取城市列表
        """
        if check_path(self.city_names):
            try:
                with pathlib.Path(self.city_names).open("r") as city_file:
                    self.citys = json.loads(city_file.read())
                    return
            except Exception as e:
                error(f"城市文件读取错误: {e}")
        try:
            resp = self.menu_session.get(self.url_list["citys"])
            self.save_debug_file(resp.text, "get_city.html")
            res = self.reg_list["citys"].findall(resp.text)
            addsucess()
            self.citys = json.loads(res[0])
            create_json(self.citys, self.city_names)
        except Exception as e:
            error(f"获取城市信息失败: {e}")
            addfailed()
            exit()
        success(f"{len(self.citys.keys())} citys")

    def menu(self):
        """
            菜单操作
        """
        while not self.current_city:
            self.get_city()
            tmp_citys = list(self.citys.items())
            for pindex, province in enumerate(tmp_citys):
                info(f"-[{pindex}]: {province[1]['name']}")
            city_index_str = input(colored("选取城市>>>", "red"))
            if not city_index_str.isdigit():
                continue
            city_index = int(city_index_str)
            city_index = 0 if city_index < 0 else city_index
            city_index = len(tmp_citys) if city_index > len(tmp_citys) else city_index
            city_target = tmp_citys[city_index]
            if city_target:
                success(f'你选择了: {city_target[1]["name"]}')
                self.current_city = city_target[1].get("short", "")
                if self.current_city:
                    while not self.current_url:
                        tmp_url_list_maps = list(self.url_list_maps.items())
                        for tindex, item in enumerate(tmp_url_list_maps):
                            info(f"-[{tindex}]: {item[1]}")
                        get_index_str = input(colored("选取类型>>>", "red"))
                        if not get_index_str.isdigit():
                            continue
                        get_index = int(get_index_str)
                        get_index = 0 if get_index < 0 else get_index
                        get_index = (
                            len(tmp_url_list_maps)
                            if get_index > len(tmp_url_list_maps)
                            else get_index
                        )
                        get_target = tmp_url_list_maps[get_index]
                        if get_target:
                            success(f"你选择了: {get_target[1]}")
                            self.current_type = get_target[0]
                            self.current_url = self.url_list.get(self.current_type, "")
                            return f'{config.datas_file}/{city_target[1]["name"]}_{get_target[1]}'

    def get_data(self, path):
        with check_times():
            try:
                trio.run(self.get_all)
                if config.more_details:
                    trio.run(self.add_detail)
            except Exception as e:
                error(e)
            finally:
                name = f'{path}_{config.status["total"]}'
                if "json" in config.export_func:
                    create_json(self.results, f"{name}.json")
                if "excel" in config.export_func:
                    pass

    def run(self):
        while True:
            self.get_data(self.menu())
            self.reset()

    def run_all(self):
        self.get_city()
        datasets = self.citys.items()
        for _, item in (
            datasets
            if config.need_city == "__all__"
            else filter(lambda item: item[1]["name"] in config.need_city, datasets)
        ):
            for tp in config.need_types:
                self.current_city = item["short"]
                self.current_type = tp
                self.current_url = self.url_list[tp]
                info(self.current_city)
                info(self.current_type)
                filenameStart = (
                    f'{config.datas_file}/{item["name"]}_{self.url_list_maps[tp]}'
                )
                self.get_data(filenameStart)
                self.reset()


@click.command()
@click.option("-a", "--run_all", default=False, type=click.BOOL, help="整站爬取")
@click.option("-m", "--more_details", is_flag=True, help="获取详情")
def start(run_all, more_details):
    try:
        spider = LIANJIA()
        trio.run(spider.ready)
        config.more_details = more_details
        config.run_all = run_all
        if config.run_all:
            spider.run_all()
        else:
            spider.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        raise e
    finally:
        info("finished")


if __name__ == "__main__":
    start()
