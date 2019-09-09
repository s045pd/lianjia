from urllib.parse import urljoin, urlparse

import moment
import numpy
from pyquery import PyQuery as jq

from common import addtotal, addupdate
from log import success, info


def parser_select(text, url, types, city):
    jqdata = jq(text)
    payload = {}

    try:
        if types == "old":
            for item in jqdata(".pictext").items():
                urlpath = item(".a_mask").attr("href")
                hid = urlpath.split("/")[-1].split(".")[0]
                url = urljoin(url, urlpath)
                roomtype, area, direction, addr = item(".item_other").text().split("/")
                title = item(".item_other").attr("title")
                payload[hid] = {
                    "hid": hid,
                    "city": city,
                    "url": url,
                    "img_main": item(".media_main>img").attr("src"),
                    "title": item(".item_main").text(),
                    "addrtype": title,
                    "roomtype": roomtype,
                    "area": float(str(area).replace("m²", "")),
                    "direction": str(direction).split(),
                    "community": addr,
                    "tags": item(".tag_box").text().split(),
                    "price_sum": float(item(".price_total>em").text()),
                    "price_avg": float(item(".unit_price").text().replace("元/平", "")),
                }
                addtotal()
                success(f"{hid} {title}")

        elif types == "old_details":
            jqdetail = jqdata(".house_description")
            jqdetail.remove("span")
            locationQuery = urlparse(
                jqdata("div.sub_mod_box.location > .mod_cont > a").attr("href")
            ).query
            levelType, levelNum = jqdetail("ul > li:nth-child(5)").text().split("/")
            agents = []
            for recommend in jqdata(".recommend_list").items():
                agents.append(
                    {
                        "url": urljoin(url, recommend(".agent_name_text").attr("href")),
                        "name": recommend(".agent_name_text").text(),
                        "img": recommend(".post_ulog>a>img").attr("src"),
                        "score": str(
                            recommend(".recommend_agent_score").text()
                        ).replace("暂无评分", ""),
                        "commany": recommend(".recommend_agent_company").text(),
                        "tel": dict(
                            [
                                item.split("=")
                                for item in recommend('a[data-act="telphone"]')
                                .attr("data-query")
                                .split("&")
                            ]
                        ).get("tel", ""),
                    }
                )
            info(str(jqdetail("ul > li:nth-child(3)").text()))
            payload = {
                "hangtag": moment.date(
                    str(jqdetail("ul > li:nth-child(3)").text())
                ).format("YYYY-MM-DD"),
                "levelType": levelType,
                "levelNum": int(levelNum),
                "style": str(jqdetail("ul > li:nth-child(6)").text()).replace(
                    "暂无数据", ""
                ),
                "elevator": True
                if "有电梯" in str(jqdetail("ul > li:nth-child(7)").text())
                else False,
                "decoration": jqdetail("ul > li:nth-child(8)").text(),
                "decade": str(jqdetail("ul > li:nth-child(9)").text()).replace("-", ""),
                "useage": jqdetail("ul > li:nth-child(10)").text(),
                "ownership": jqdetail("ul > li:nth-child(11)").text(),
                "location": dict(
                    [item.split("=") for item in locationQuery.split("&")]
                ).get("pos", "")
                if locationQuery
                else "",
                "agents": agents,
                "address": jqdata(".marker_title").text(),
                "details": jqdata(".house_intro_mod_cont").text(),
                "day7": int(
                    jqdata(
                        " div.mod_box.house_record > div.mod_cont > div > div:nth-child(1) > strong"
                    ).text()
                ),
                "day30": int(
                    jqdata(
                        " div.mod_box.house_record > div.mod_cont > div > div:nth-child(2) > strong"
                    ).text()
                ),
                "attention": int(
                    jqdata(
                        " div.mod_box.house_record > div.mod_cont > div > div:nth-child(3) > strong"
                    ).text()
                ),
            }
            addupdate()

        elif types == "new":
            for item in jqdata(".resblock-list-item").items():
                hid = item(".resblock-info").attr("data-uid")
                area = item(".area").text().split()
                payload[hid] = {
                    "hid": hid,
                    "city": city,
                    "url": urljoin(url, item(".resblock-info").attr("href")),
                    "title": item(".name").text(),
                    "addrtype": item(".desc").text(),
                    "roomtype": item(".resblock-location-line").text(),
                    "tags": str(item(".resblock-tags-line").text()).split(),
                    "price_sum": item(".price_num").text(),
                    "price_bunch": item(".price_bunch").text(),
                    "area": str(area[-1]).replace("m²", "") if area else "",
                }
                addtotal()
                success(payload[hid]["title"])

        elif types == "new_details":
            location_jq = urlparse(
                jqdata(".change-price-address > div:nth-child(3) > a").attr("href")
            ).query
            huxings = []
            for item in jqdata(".huxing-list-item").items():
                huxings.append(
                    {
                        "img_main": item("img.huxing-img").attr("src"),
                        "room_umber": item(".room-number").text(),
                        "insale": True
                        if item(".status-in-sale").text() == "在售"
                        else False,
                        "area": item(".huxing-area >a:nth-child(1)").text(),
                        "direction": item(".huxing-area >a:nth-child(2)").text(),
                        "price": item(".price").text(),
                        "tags": item(".tag-wrapper").text().split(),
                    }
                )
            payload = {
                "hangtag": moment.date(jqdata(".open-time").text()).format(
                    "YYYY-MM-DD"
                ),
                "address": jqdata(
                    ".change-price-address > div:nth-child(3) > a"
                ).text(),
                "location": dict(
                    [item.split("=") for item in location_jq.split("&")]
                ).get("pos", "")
                if location_jq
                else "",
                "more": urljoin(url, jqdata(".more-building-detail a").attr("href")),
                "huxings": huxings,
                "tel": jqdata(".call_phone").attr("data-phone-num"),
            }
            addupdate()

        elif types == "chuzu":

            for item in jqdata('div[data-el="houseItem"]').items():
                hid = item.attr("data-housecode")
                price = item(".content__item__bottom").text().replace("元/月", "").strip()
                try:
                    price = (
                        int(price)
                        if price.isdigit()
                        else int(numpy.mean(list(map(int, price.split("-")))))
                        if "-" in price
                        else 0
                    )
                except ValueError:
                    price = 0
                payload[hid] = {
                    "hid": hid,
                    "city": city,
                    "url": urljoin(url, item('[data-el="jumpDetailEl"]').attr("href")),
                    "title": item(".content__item__aside").attr("alt"),
                    "img_main": item(".content__item__aside").attr("src"),
                    "tags": item(".content__item__tag--wrapper").text().split(),
                    "price": price,
                }
                success(f"{payload[hid]['title']} {payload[hid]['price']}")
                addtotal()

        elif types == "chuzu_details":
            location_jq = urlparse(
                jqdata(".map--container >img").attr("data-src")
            ).query
            other = {
                item("label").text().replace("：", ""): item("span").text()
                for item in jqdata(".page-house-info-list li").items()
            }
            for index, item in enumerate("一 二 三 四 五 六 七 八 大 九 十 十一 十二".split()):
                other["发布"] = other["发布"].replace(item, str(index + 1))
            payload = {
                "description": jqdata(".page-house-description-list").text().split(),
                "details": jqdata(".box.detail").text(),
                "area_type": jqdata(
                    "div.box.content__detail--info > ul > li:nth-child(2) > span:nth-child(2)"
                ).text(),
                "area": jqdata(
                    "div.box.content__detail--info > ul > li:nth-child(3) > span:nth-child(2)"
                ).text(),
                "location": dict(
                    [item.split("=") for item in location_jq.split("&")]
                ).get("center", "")
                if location_jq
                else "",
                "hangtag": moment.date(other["发布"]).format("YYYY-MM-DD"),
                "checkin": other["入住"],
                "view": other["看房"],
                "levelType": other["楼层"].split("/")[0],
                "levelNum": int(other["楼层"].split("/")[1].replace("层", "")),
                "elevator": True if "有" in other["电梯"] else False,
                "parking": True if "有" in other["车位"] else False,
                "water": True if "有" in other["用水"] else False,
                "power": True if "有" in other["用电"] else False,
                "gas": True if "有" in other["燃气"] else False,
                "heater": True if "有" in other["采暖"] else False,
            }
            addupdate()

    except Exception as e:
        raise

    return payload
