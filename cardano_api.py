#!/usr/bin/env python
# _*_ coding: utf-8 _*_

import sys, os, traceback, json, operator
import pyjsonrpc
import hashlib

from py2mylib.mylog import *
from py2mylib.base import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from rpc.rpc_base import *

#ada最小单位换算
ADA2LOVELACES = 1000000
TTL_ADD = 5000000
CUR_PATH = os.path.dirname(__file__)
CARDANO_CLI = os.path.join(CUR_PATH, "cardano-cli")
TRANS_PATH = os.path.join(CUR_PATH, "txs/")

class CoinApi(CoinApiBase):
    #############基类接口#############
    @CoinApiMethod
    def GetTransactionById(self, txid):
        requrl = "{}/api/txs/summary/{}".format(self.GetNodehost(), txid)
        respone = HttpGet(requrl)
        isSucc = False
        transaction = {}
        if respone and "Right" in respone:
            vin = []
            for input in respone["Right"]["ctsInputs"]:
                simple_input = self.GetSimpleVinOut(input)
                vin.append(simple_input)
            vout = []
            for output in respone["Right"]["ctsOutputs"]:
                simple_output = self.GetSimpleVinOut(output)
                vout.append(simple_output)
            transaction = self.MakeAdaTransaction("", "", vout[0]["txid"], -1, respone["Right"]["ctsBlockHeight"],
                                                  respone["Right"]["ctsBlockTimeIssued"],
                                                  respone["Right"]["ctsBlockHash"], vin, vout,
                                                  str(float(respone["Right"]["ctsFees"]["getCoin"]) / ADA2LOVELACES))
            isSucc = True
        return (isSucc, transaction)

    @CoinApiMethod
    def GetAccountInfo(self, address):
        requrl = "{}/api/addresses/summary/{}".format(self.GetNodehost(), address)
        respone = HttpGet(requrl)
        return (True, respone)

    @CoinApiMethod
    def GetBlockByHash(self, blockhash):
        requrl = "{}/api/blocks/summary/{}".format(self.GetNodehost(), blockhash)
        respone = HttpGet(requrl)
        isSucc = False
        block = {}
        if respone and "Right" in respone:
            block = {
                "blocktime": respone["Right"]["cbsEntry"]["cbeTimeIssued"],
                "blockheight": respone["Right"]["cbsEntry"]["cbeBlkHeight"],
                "blockhash": respone["Right"]["cbsEntry"]["cbeBlkHash"],
                "txnum": respone["Right"]["cbsEntry"]["cbeTxNum"],
                "totalesent": respone["Right"]["cbsEntry"]["cbeTotalSent"]["getCoin"],
                "totalfees": respone["Right"]["cbsEntry"]["cbeFees"]["getCoin"]
            }
            isSucc = True
        return (isSucc, block)

    @CoinApiMethod
    def GetBlockByHeight(self, height):
        return (False, "GetBlockByHeight==> Not implemented")

    @CoinApiMethod
    def GetBlockHashByHeight(self, height):
        isSucc = False
        blockhash = ""
        if height > 0:
            page = height / 10 + (1 if height % 10 is not 0 else 0)
            requrl = "{}/api/blocks/pages?page={}".format(self.GetNodehost(), page)
            respone = HttpGet(requrl)
            if respone and len(respone["Right"]) > 1 and len(respone["Right"][1]) > 0:
                for block in respone["Right"][1]:
                    if operator.eq(block["cbeBlkHeight"], height):
                        blockhash = block["cbeBlkHash"]
                        isSucc = True
                        break
        return (isSucc, blockhash)

    @CoinApiMethod
    def GetBlockCount(self, pagesize=1):
        requrl = "{}/api/blocks/pages/total?pageSize={}".format(self.GetNodehost(), pagesize)
        respone = HttpGet(requrl)
        isSucc = False
        blockheight = -1
        if respone:
            blockheight = respone["Right"]
            isSucc = True
        return (isSucc, blockheight)

    @CoinApiMethod
    def SendRawTransaction(self, tran_raw):
        """
        :param tran_raw:
        {
            "tx_signed": "",
            "md5":
        }
        :return:
        """
        build_tx_file = os.path.join(TRANS_PATH, "{}.raw".format(tran_raw["md5"]))
        if not os.path.exists(build_tx_file):
            raise Exception("SendRawTransaction==> tx.raw file {} not exists!".format(build_tx_file))
        txid = CmdCall("{} shelley transaction txid --tx-body-file {}".format(CARDANO_CLI, build_tx_file), False, False)
        tx_signed_file = os.path.join(TRANS_PATH, "{}.signed".format(tran_raw["md5"]))
        f = open(tx_signed_file, "w")
        json.dump(tran_raw["tx_signed"], f)
        f.close()
        tx_submit_cmd = "{} shelley transaction submit --tx-file {} --mainnet".format(CARDANO_CLI, tx_signed_file)
        CmdCall(tx_submit_cmd, False, False)
        MyLog.Logger.info("SendRawTransaction==> End")
        return (True, txid)

    @CoinApiMethod
    def SignTransaction(self, draw_text):
        """
        :param draw_text:{
            "draw_text": tran_text,
            "md5": tran_text_md5,
            "input_addrs": input_addrs_set,
            "tx_raw": tx_raw,
        }
        :return:
        """
        if not os.path.exists(TRANS_PATH):
            os.mkdir(TRANS_PATH)
        tx_signed_file = os.path.join(TRANS_PATH, "{}.signed".format(draw_text["md5"]))
        signkeys_addrs = ""
        for addr in draw_text["input_addrs"]:
            prikeyfile = self.GetPrivateFile(addr)
            if not prikeyfile:
                raise Exception("SignTransaction==> GetPrivateFile [addr={}] failed!".format(addr))
            signkeys_addrs += "--signing-key-file {} --address {} ".format(prikeyfile, addr)
        tx_body_file = os.path.join(TRANS_PATH, "{}.raw".format(draw_text["md5"]))
        f = open(tx_body_file, "w")
        json.dump(draw_text["tx_raw"], f)
        f.close()
        if not os.path.exists(tx_body_file):
            raise Exception("SignTransaction==> Save tx body file {} failed!".format(tx_body_file))
        tx_signed_cmd = "{} shelley transaction sign {} --tx-body-file {} --mainnet --out-file {}".format(CARDANO_CLI, signkeys_addrs, tx_body_file, tx_signed_file)
        CmdCall(tx_signed_cmd, False, False)
        if not os.path.exists(tx_signed_file):
            raise Exception("SignTransaction==> Signed tx failed! {} ".format(tx_signed_file))
        MyLog.Logger.info("SignTransaction==> Signed tx success {}".format(tx_signed_file))
        f = open(tx_signed_file, "r")
        tx_signed = json.load(f)
        f.close()
        return (True,   {
            "tx_signed": tx_signed,
            "md5":draw_text["md5"]
        })

    #############子类接口#############
    def CreateTransaction(self, tran_text):
        """
        解析tran_text通过cardano-cli命令行工具创建交易，并以 md5(json2str(tran_text)).text命名保存到 txs目录下, 返回{"md5":"","draw_text":{}}
        :param tran_text:
        [
          [
            {
              "address": "DKgCguR11mX3zEMQ8AgJ4nV9mEDpsn1gzo",
              "amount": 86574.57642878,
              "id": "9011",
              "scriptPubKey": "76a9149f73c9ed101af61fe272ab65a516762b72c0964a88ac",
              "txid": "ef630e7cd15f56db4f29547e355591ac0931690696ea59f58c08c9cd80994ea8",
              "vout": 1
            }
          ],
          {
            "DKgCguR11mX3zEMQ8AgJ4nV9mEDpsn1gzo": "82151.96323868",
            "DTVX1aCTGJCdPncwygCfb5zsRZZzaekkpM": "4422.23319010"
          },
          "找零地址"
        ]
        :return:
        """
        MyLog.Logger.info("CreateTransaction==> {}".format(json.dumps(tran_text)))
        if not os.path.exists(TRANS_PATH):
            os.mkdir(TRANS_PATH)
        txin = ""
        input_addrs_set = []
        input_sum = 0
        for vin in tran_text[0]:
            txin += "--tx-in {}#{} ".format(vin["txid"], vin["vout"])
            input_addrs_set.append(vin["address"])
            input_sum += int(float(vin["amount"]) * ADA2LOVELACES)
        input_addrs_set = list(set(input_addrs_set))
        txout_withdraw = ""
        txout_draft = ""
        withdraw_sum = 0
        for vout in tran_text[1]:
            out_lovelaces = int(float(tran_text[1][vout]) * ADA2LOVELACES)
            txout_withdraw += "--tx-out {}+{} ".format(vout, out_lovelaces)
            txout_draft += "--tx-out {}+0 ".format(vout)
            withdraw_sum += out_lovelaces
        txout_draft += "--tx-out {}+0".format(tran_text[2])
        tran_text_md5 = hashlib.md5(json.dumps(tran_text)).hexdigest()
        draft_tx_file = os.path.join(TRANS_PATH, "{}.draft".format(tran_text_md5))

        # Draft the transaction
        draft_tx_cmd = "{} shelley transaction build-raw {} {} --ttl 0 --fee 0 --out-file {}".format(CARDANO_CLI, txin, txout_draft, draft_tx_file)
        CmdCall(draft_tx_cmd, False, False)
        if not os.path.exists(draft_tx_file):
            raise Exception("CreateTransaction==> Draft transaction failed!")
        MyLog.Logger.info("CreateTransaction==> Draft the transaction success {}".format(draft_tx_file))

        # Calculate the fee && ttl
        protocol_file = os.path.join(CUR_PATH, "protocol.json")
        CmdCall("./cardano-cli shelley query protocol-parameters --mainnet  --out-file {}".format(protocol_file), False, False)
        if not os.path.exists(protocol_file):
            raise Exception("CreateTransaction==> Get protocol parameters failed!")
        MyLog.Logger.info("CreateTransaction==> Query protocol-parameters success...")
        calc_tranfee_cmd = "{} shelley transaction calculate-min-fee --tx-body-file {} --tx-in-count {} --tx-out-count {} --witness-count {} --byron-witness-count {} --mainnet --protocol-params-file {}".format(
            CARDANO_CLI, draft_tx_file, len(tran_text[0]), len(tran_text[1]) + 1, len(tran_text[0]), len(tran_text[0]), protocol_file
        )
        fee = int(CmdCall(calc_tranfee_cmd, False, False).split(" ")[0])
        # fee = input_sum - withdraw_sum
        MyLog.Logger.info("CreateTransaction==> Calculate the fee success {}".format(fee))
        tip = CmdCall("{} shelley query tip --mainnet".format(CARDANO_CLI), False, True)
        MyLog.Logger.info("CreateTransaction==> Query tip success {}".format(json.dumps(tip)))
        ttl = tip["slotNo"] + TTL_ADD

        # build the transaction
        subzero = input_sum - withdraw_sum - fee
        if subzero > ADA2LOVELACES: # output必须大于1ADA，否则无法广播成功
            txout_withdraw += "--tx-out {}+{}".format(tran_text[2], subzero)
        else:
            fee = input_sum - withdraw_sum
        build_tx_file = os.path.join(TRANS_PATH, "{}.raw".format(tran_text_md5))
        build_tx_cmd = "{} shelley transaction build-raw {} {} --ttl {} --fee {} --out-file {}".format(CARDANO_CLI, txin, txout_withdraw, ttl, fee, build_tx_file)
        CmdCall(build_tx_cmd, False, False)
        if not os.path.exists(build_tx_file):
            raise Exception("CreateTransaction==> Build the transaction failed!")
        MyLog.Logger.info("CreateTransaction==> Build the transaction success {}".format(build_tx_file))
        tx_file = open(build_tx_file, "r")
        tx_raw = json.load(tx_file)
        return (True, {
            "draw_text": tran_text,
            "md5": tran_text_md5,
            "input_addrs": input_addrs_set,
            "tx_raw": tx_raw,
        })

    def GetUtxo(self, addr):
        requrl = "{}/mainnet/utxos/{}".format(self.GetNodehost(), addr)
        result = HttpGet(requrl)
        return (True, result)

    def GetUtxoListByAddrs(self, addrs):
        result = {
            "sum": 0
        }
        for addr in addrs:
            utxos = self.GetUtxo(addr)
            for utxo in utxos:
                if utxo and utxo.has_key("txid") and utxo.has_key("index") and utxo.has_key("coin"):
                    result["sum"] += utxo["coin"]
                    result["{}_{}".format(utxo["txid"], utxo["index"])] = utxo["coin"]
        return (True, result)

    def GetSimpleVinOut(self, output):
        simple_output = {
            "address": output["ctaAddress"],
            "amount": str(float(output["ctaAmount"]["getCoin"]) / ADA2LOVELACES),
            "txid": output["ctaTxHash"],
            "txindex": output["ctaTxIndex"]
        }
        return simple_output

    def MakeAdaTransaction(self, to, value, txid, txindex, blockheight, blocktime, blockhash, vin=None, vout=None, usefee="0.0"):
        transaction = self.MakeTransaction("", to, value, txid, blockheight, blocktime, blockhash, usefee)
        transaction.update({
            "txindex": txindex,
            "vin": [] if not vin else vin,
            "vout": [] if not vout else vout,
        })
        return transaction

    def GetSimpleTxsByBlockhash(self, blockhash):
        isSucc = False
        txs = []
        requrl = "{}/api/blocks/txs/{}".format(self.GetNodehost(), blockhash)
        respone = HttpGet(requrl)
        if respone and "Right" in respone:
            isSucc, block = self.GetBlockByHash(blockhash)
            if isSucc:
                for tran in respone["Right"]:
                    for output in tran["ctbOutputs"]:
                        simple_output = self.GetSimpleVinOut(output)
                        transaction = self.MakeAdaTransaction(simple_output["address"], simple_output["amount"],
                                                              simple_output["txid"], simple_output["txindex"],
                                                              block["blockheight"], block["blocktime"],
                                                              block["blockhash"])
                        txs.append(transaction)
        return txs

    def GetPrivateFile(self, addr):
        # byron秘钥格式转换为shelley格式
        self.privatekeys = getattr(self, "privatekeys", None)
        if not self.privatekeys:
            private_keys_file = os.path.join(CUR_PATH, GlobalConfig.GetConfigValue("prvkeysfile"))
            f = open(private_keys_file, "r")
            self.privatekeys = json.load(f)
            f.close()
        addr_key_file = os.path.join(CUR_PATH, "./shelley_key/{}.skey".format(addr))
        if not os.path.exists(os.path.dirname(addr_key_file)):
            os.mkdir(os.path.dirname(addr_key_file))
        if not os.path.exists(addr_key_file):
            # shelley format key
            addr_keys = self.privatekeys.get(addr, None)
            if not addr_keys:
                raise Exception("{} private ket not found...".format(addr))
            shelley_key = {
                "type": "PaymentSigningKeyByron_ed25519_bip32",
                "description": "Payment Signing Key",
                "cborHex": "5880{}{}".format(addr_keys["addrprv"][:128], addr_keys["addrpub"])
            }
            shelley_key_file = open(addr_key_file, "w")
            json.dump(shelley_key, shelley_key_file)
            shelley_key_file.close()
        return addr_key_file

class RequestHandler(RequestHandlerBase):

    #############基类接口#############
    def GetCoinname(self):
        return "ada"

    def GetCoinApiInstance(self):
        self.__coinapi = getattr(self, "__coinapi", None)
        if not self.__coinapi:
            nodehost = GlobalConfig.GetConfigValue("cardano_explorer_host", "http://localhost:8100")
            self.__coinapi = CoinApi("ada", nodehost)
            MyLog.Logger.info("Init ada coin [nodehost={}]... ".format(nodehost))
        return self.__coinapi

    #############子类接口#############
    @pyjsonrpc.rpcmethod
    def CreateTransaction(self, *args):
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "CreateTransaction args={} len must be 1".format(args))
        return self.handleExec("CreateTransaction", args)

    @pyjsonrpc.rpcmethod
    def GetUtxo(self, *args):
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetUtxo args={} len must be 1".format(args))
        return self.handleExec("GetUtxo", args)

    @pyjsonrpc.rpcmethod
    def GetUtxoListByAddrs(self, *args):
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetUtxoListByAddrs args={} len must be 1".format(args))
        return self.handleExec("GetUtxoListByAddrs", args)

    @pyjsonrpc.rpcmethod
    def GetSimpleTxsByBlockhash(self, *args):
        if not operator.eq(len(args), 1):
            return self.MakeResp(False, "GetSimpleTxsByBlockhash args={} len must be 1".format(args))
        return self.handleExec("GetSimpleTxsByBlockhash", args)