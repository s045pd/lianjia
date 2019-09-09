import requests
from celery import Celery

from conf import config
from log import error, success, warning
from mongomodels import agent, oldHouse, newHouse, chuzuHouse

app = Celery("darknet", broker=f"sqla+sqlite:///{config.celery_db}")


@app.task()
def save_to_mongo(datas, types):
    orm_map = {"old": oldHouse, "agent": agent, "new": newHouse, "chuzu": chuzuHouse}
    target = orm_map.get(types)
    if target:
        success(target(**datas).save())
