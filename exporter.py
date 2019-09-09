import json

import pandas

from common import check_path, check_times
from log import success


def create_xlsx(datas, columns, filename="res.xlsx"):
    if not datas:
        return
    with check_times():
        xlsx = pandas.DataFrame(datas)
        xlsx.rename(columns=columns, inplace=True)
        writer = pandas.ExcelWriter(filename, options={"strings_to_urls": False})
        xlsx.to_excel(writer, "data")
        writer.save()
        success("Created {filename}")


def create_json(datas, filename="res.json"):
    if not datas:
        return
    with check_times():
        with open(filename, "w") as f:
            f.write(json.dumps(datas, ensure_ascii=False, indent=4))
            success(f"Saved {filename}")
