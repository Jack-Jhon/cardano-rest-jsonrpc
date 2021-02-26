#!/usr/bin/env python
# _*_ coding: utf-8 _*_

import sys, os, traceback, pyjsonrpc, json, operator
import imp
from py2mylib.mylog import *

# jsonrpc method base interface
class RequestHandlerBase(pyjsonrpc.HttpRequestHandler):

    def GetCoinname(self):
        raise Exception("Child class not implemented [func=GetCoinname]!")

    def GetCoinApiInstance(self):
        raise Exception("Child class not implemented [func=GetCoinApiInstance]!")

    def MakeResp(self, bret, respone):
        result = {
            "code": -1,
            "errmsg": ""
        }
        if bret:
            result["code"] = 1
            result["errmsg"] = "success"
            result["result"] = respone
        else:
            result["errmsg"] = respone
        return result

    def handleExec(self, func, args):
        """
        python-jsonrpc 统一处理函数
        :param func: 函数名, 字符串, 返回值需要为 (bool, result), 否则报错
        :param args: 入参，列表/元组传递 *args
        :return:
        """
        bret = False
        respone = ""
        try:
            MyLog.Logger.info("{}.{} req ==> {}".format(self.GetCoinname(), func, args))
            if not isinstance(args, tuple):
                raise Exception("args {} not tuple".format(args))
            run = eval("self.GetCoinApiInstance().{}".format(func))
            bret, respone = run() if len(args) is 0 else run(*args)
        except Exception as err:
            ls_format_exc = str(traceback.format_exc()).split("\n")
            respone = {
                "Exception": str(err),
                "ls_format_exc": ls_format_exc
            }
            MyLog.Logger.error("except [err={}]".format(err))
            MyLog.Logger.error(traceback.format_exc())
        result = self.MakeResp(bret, respone)
        MyLog.Logger.info("{}.{} resp ==> {}".format(self.GetCoinname(), func, json.dumps(result)))
        return result

    @pyjsonrpc.rpcmethod
    def GetTransactionById(self, *args):
        """
        获取交易详情
        :param args: [txid]
        :return:
        """
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetTransactionById args={} len must be 1".format(args))
        return self.handleExec("GetTransactionById", args)

    @pyjsonrpc.rpcmethod
    def GetAccountInfo(self, *args):
        """
        获取账户详情
        :param args: [address]
        :return:
        """
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetAccountInfo args={} len must be 1".format(args))
        return self.handleExec("GetAccountInfo", args)

    @pyjsonrpc.rpcmethod
    def GetBlockByHash(self, *args):
        """
        获取区块详情
        :param args: [blockhash]
        :return:
        """
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetBlockByHash args={} len must be 1".format(args))
        return self.handleExec("GetBlockByHash", args)

    @pyjsonrpc.rpcmethod
    def GetBlockHashByHeight(self, *args):
        """
        获取区块哈希
        :param args: [blockheight]
        :return:
        """
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetBlockHashByHeight args={} len must be 1".format(args))
        return self.handleExec("GetBlockHashByHeight", args)

    @pyjsonrpc.rpcmethod
    def GetBlockCount(self, *args):
        """
        获取当前区块高度
        :param args: []
        :return:
        """
        return self.handleExec("GetBlockCount", args)

    @pyjsonrpc.rpcmethod
    def SendRawTransaction(self, *args):
        """
        广播签名交易
        :param args: [{tran_raw}]
        :return:
        """
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "SendRawTransaction args={} len must be 1".format(args))
        return self.handleExec("SendRawTransaction", args)

    @pyjsonrpc.rpcmethod
    def SignTransaction(self, *args):
        """
        (离线)签名交易
        :param args: [{tran_text}]
        :return:
        """
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "SignTransaction args={} len must be 1".format(args))
        return self.handleExec("SignTransaction", args)

# coin api interface
def CoinApiMethod(func):
    # CoinApi函数签名装饰器
    func.coinapimethod = True
    return func

class CoinApiBase(object):

    def __init__(self, coinname, nodehost):
        self.__coinname = coinname
        self.__nodehost = nodehost
        # 每个链的rpc, 必须实现这 7个函数, 不需要用到的子类继承后可不实现，返回值固定为 (bool, result)
        mustfuncnames = ["GetTransactionById", "GetAccountInfo", "GetBlockByHash", "GetBlockByHeight", "GetBlockHashByHeight", "GetBlockCount", "SendRawTransaction", "SignTransaction"]
        for fname in mustfuncnames:
            _func = getattr(self, fname, None)
            if not (_func and callable(_func) and getattr(_func, "coinapimethod", False)):
                raise Exception("has not [funcname={}] is requirements!".format(fname))

    def GetCoinname(self):
        return self.__coinname

    def GetNodehost(self):
        return self.__nodehost

    def MakeTransaction(self, sender, to, value, txid, blockheight, blocktime, blockhash, usefee="0.0"):
        # 最终的交易结构字段是冗余的
        transaction = {
            "from": sender,
            "to": to,
            "value": value,
            "txid": txid,
            "blockheight": blockheight,
            "blocktime": blocktime,
            "blockhash": blockhash,
            "coinname": self.GetCoinname().lower(),
            "usefee": usefee
        }
        return transaction

    def MakeBlock(self):
        pass

    def MakeSignTransaction(self):
        pass

    def MakeAccountInfo(self):
        pass