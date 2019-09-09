<h1 align="center">Lianjia Downloader 👋</h1>
<p align="center">
  <a href="https://github.com/kefranabg/readme-md-generator/blob/master/LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" target="_blank" />
  </a>
  <a target="_blank" href="https://www.python.org/downloads/" title="Python version"><img src="https://img.shields.io/badge/python-%3E=_3.7.4-green.svg"></a>
</p>

> 通过命令行脚本快速下载地区信息

## 安装

首先你得确认你已经安装了`python3`,然后我们运行如下命令来安装依赖。

```sh
python3 -m pip install -r requirements.txt
```

## 用法

我们通过如下命令查看部分可用参数。

配置```config.py```

```sh
mongo_uri = '...'
```

```sh
python3 main.py --help

  -a, --run_all BOOLEAN  整站爬取
  -m, --more_details     获取详情
  --help                 Show this message and exit.
```

开启```celery```，将结果存至```mongodb```

```sh
celery -B -A task worker -l info
```

开始爬行,包含详情

```sh
python3 main.py -m
```


## 📝 License

This project is [MIT](https://github.com/kefranabg/readme-md-generator/blob/master/LICENSE) licensed.

***