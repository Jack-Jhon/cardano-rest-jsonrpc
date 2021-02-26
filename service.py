#!/usr/bin/env python
# _*_ coding: utf-8 _*_
import sys
import os

from py2mylib.base import *
from py2mylib.mylog import *
import logging
import pyjsonrpc
import traceback
import imp
from rpc_base import *

if __name__ == '__main__':
    try:
        if len(sys.argv[1:]) < 1:
            raise Exception("Not input coin name")
        coinname = sys.argv[1:][0]
        curpath = os.path.dirname(__file__)
        LogPath = os.path.join(curpath, "../log/{}".format(coinname))
        LogLevel = logging.DEBUG
        # 日志需要最先初始化
        MyLog.InitLog(LogPath, LogLevel)
        GlobalConfig.LoadConfig(os.path.join(curpath, "../config"))
        url = GlobalConfig.GetConfigValue("rpcip", "0.0.0.0")
        port = GlobalConfig.GetConfigValue("rpcport", 9989)
        coin_class = imp.load_source(coinname, os.path.join(os.path.dirname(__file__), "./{}/{}_rpc.py".format(coinname, coinname)))
        http_server = pyjsonrpc.ThreadingHttpServer(
            server_address=(url, port),
            RequestHandlerClass=coin_class.RequestHandler
        )
        MyLog.Logger.info("Starting {} rpc server ...URL: http://{}:{}".format(coinname, url, port))
        http_server.serve_forever()
    except Exception as err:
        MyLog.Logger.error("except [err={}]".format(err.message))
        MyLog.Logger.error(traceback.format_exc())
