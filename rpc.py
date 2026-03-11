# from __future__ import print_function

import random
import hashlib
import json
import binascii
# import time
# import pathlib

import tornado.web
import tornado.gen
import tornado.escape
# import tornado.ioloop
# import tornado.httpserver
# import tornado.httpclient

# import rocksdb
import web3
import eth_account
import hexbytes
import rlp

import space
import sys
import os
import importlib.util

CHAIN_ID = 31337
REVERSED_NO = 10**16

# pathlib.Path("states").mkdir(parents=True, exist_ok=True)
# conn = rocksdb.DB('states/tempchain.db', rocksdb.Options(create_if_missing=True))

try:
    web3.Web3.toChecksumAddress = web3.Web3.to_checksum_address
except:
    pass

# class Application(tornado.web.Application):
#     def __init__(self):
#         handlers = [
#             (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static/"}),
#             (r"/", RPCHandler)
#         ]
#         settings = {"debug":True}

#         tornado.web.Application.__init__(self, handlers, **settings)


latest_block_number = 0
# latest_block_hash = b'\x00'*32
# it = conn.iteritems()
# k = 'blockno-'
# it.seek(k.encode('utf8'))
# for key, value_json in it:
#     print(key)
#     if not key.startswith('blockno-'.encode('utf8')):
#         break

#     _, reverse_block_number, block_hash = key.decode('utf8').split('-')
#     latest_block_number = REVERSED_NO - int(reverse_block_number)
#     latest_block_hash = binascii.unhexlify(block_hash)
#     break

block_filters = {}
# transaction_queue = []
blocks = {}
transactions = {}
accounts = {}


V_OFFSET = 27
def eth_rlp2list(tx_rlp_bytes):
    if tx_rlp_bytes.startswith(b'\x02'):
        tx_rlp_list = rlp.decode(tx_rlp_bytes[1:])
        #print('eth_rlp2list type2', tx_rlp_list)
        chain_id = int.from_bytes(tx_rlp_list[0], 'big')
        nonce = int.from_bytes(tx_rlp_list[1], 'big')
        gas_price = int.from_bytes(tx_rlp_list[2], 'big')
        max_priority = int.from_bytes(tx_rlp_list[3], 'big')
        max_fee = int.from_bytes(tx_rlp_list[4], 'big')
        to = web3.Web3.toChecksumAddress(tx_rlp_list[5])
        value = int.from_bytes(tx_rlp_list[6], 'big')
        data = tx_rlp_list[7].hex()
        v = int.from_bytes(tx_rlp_list[9], 'big')
        r = int.from_bytes(tx_rlp_list[10], 'big')
        s = int.from_bytes(tx_rlp_list[11], 'big')
        return [chain_id, nonce, gas_price, max_priority, max_fee, to, value, data], [v, r, s]

    else:
        tx_rlp_list = rlp.decode(tx_rlp_bytes)
        #print('eth_rlp2list', tx_rlp_list)
        nonce = int.from_bytes(tx_rlp_list[0], 'big')
        gas_price = int.from_bytes(tx_rlp_list[1], 'big')
        gas = int.from_bytes(tx_rlp_list[2], 'big')
        to = web3.Web3.toChecksumAddress(tx_rlp_list[3])
        value = int.from_bytes(tx_rlp_list[4], 'big')
        data = tx_rlp_list[5].hex()
        v = int.from_bytes(tx_rlp_list[6], 'big')
        r = int.from_bytes(tx_rlp_list[7], 'big')
        s = int.from_bytes(tx_rlp_list[8], 'big')
        chain_id, chain_naive_v = eth_account._utils.signing.extract_chain_id(v)
        v_standard = chain_naive_v - V_OFFSET
        return [nonce, gas_price, gas, to, value, data, chain_id], [v_standard, r, s]

welcome_message = '''Chain id: %s
RPC: http://127.0.0.1:8545/rpc

pip install eth-brownie
brownie networks add playground host=http://127.0.0.1:8545 chainid=%s
brownie console --network playground
''' % (CHAIN_ID, CHAIN_ID)
# HTTP_PROXY=127.0.0.1:7890 brownie console --network playground
# brownie console --network hardhat

class RPCHandler(tornado.web.RequestHandler):
    def get(self):
        self.finish(welcome_message.replace('\n', '<br>'))

    @tornado.gen.coroutine
    def post(self):
        global blocks
        global transactions
        global accounts
        global latest_block_number

        self.add_header('access-control-allow-methods', 'OPTIONS, POST')
        self.add_header('access-control-allow-origin', 'moz-extension://52ed146e-8386-4e74-9dae-5fe4e9ae20c8')

        req = tornado.escape.json_decode(self.request.body)
        print(req['method'])
        rpc_id = req['id']

        # 处理自定义逻辑函数调用
        if req.get('method') == 'zentra_call':
            # 延迟导入，避免循环依赖
            from play import GLOBAL_FUNCTIONS
            func_name = req['params'][0]
            args = req['params'][1] if len(req['params']) > 1 else {}
            info = req['params'][2] if len(req['params']) > 2 else {'sender': space.sender}
            if func_name in GLOBAL_FUNCTIONS:
                try:
                    result = GLOBAL_FUNCTIONS[func_name](info, args)
                    resp = {'jsonrpc': '2.0', 'result': result, 'id': rpc_id}
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    resp = {'jsonrpc': '2.0', 'error': str(e), 'id': rpc_id}
            else:
                resp = {'jsonrpc': '2.0', 'error': f'Method {func_name} not found in ZIPs', 'id': rpc_id}
            self.write(tornado.escape.json_encode(resp))
            return
        if req.get('method') == 'eth_chainId':
            resp = {'jsonrpc':'2.0', 'result': hex(CHAIN_ID), 'id':rpc_id}

        elif req.get('method') == 'eth_blockNumber':
            block_number = latest_block_number
            resp = {'jsonrpc':'2.0', 'result': hex(block_number), 'id':rpc_id}

        elif req.get('method') == 'eth_getBlockByNumber':
            block_number = req['params'][0]
            if block_number == 'latest':
                block_number = latest_block_number
            else:
                block_number = int(block_number, 16)

            block_hash = '0x0000000000000000000000000000000000000000000000000000000000000000'
            if block_number - 1 in blocks:
                block_hash = '0x' + blocks[block_number - 1]
            print('eth_getBlockByNumber', block_number, block_hash)

            result = {
                'number': hex(block_number),
                'hash': block_hash,
                'timestamp': '0',
                'gasLimit': '0x1c9c380'
            }

            resp = {'jsonrpc':'2.0', 'result': result, 'id':rpc_id}

        elif req.get('method') == 'eth_getBalance':
            address = web3.Web3.toChecksumAddress(req['params'][0])
            block_height = req['params'][1]
            if block_height == 'latest':
                block_height = latest_block_number

            resp = {'jsonrpc':'2.0', 'result': hex(1000000000000000000), 'id':rpc_id}

        elif req.get('method') == 'eth_getTransactionReceipt':
            transaction_hash = req['params'][0]
            print(transaction_hash)
            # receipt_json = receipts_tree[transaction_hash.replace('0x', '').encode('utf8')]
            # transaction_json = conn.get(('transaction-%s' % transaction_hash.replace('0x', '')).encode('utf8'))
            # receipt = json.loads(transaction_json)
            receipt = transactions.get(transaction_hash.replace('0x', '').lower())
            print(receipt)
            block_number = receipt['blockNumber']
            block_hash = '0x'+receipt['block_hash']
            tx_from = receipt['from']

            result = {
                'transactionHash': transaction_hash,
                'transactionIndex': hex(0),
                'blockHash': block_hash,
                'blockNumber': hex(block_number),
                'from': tx_from,
                'cumulativeGasUsed': 0,
                'gasUsed': 0,
                'contractAddress': None,
                'status': hex(1),
                'logs': [
                    {
                        "address":"0x"+'0'*40,
                        "blockHash":"0x0a79eca9f5ca58a1d5d5030a0fabfdd8e815b8b77a9f223f74d59aa39596e1c7",
                        "blockNumber":"0x11e5883",
                        "transactionHash": "0x7114b4da1a6ed391d5d781447ed443733dcf2b508c515b81c17379dea8a3c9af",
                        "transactionIndex": "0x1",
                        "data":"0x00000000000000000000000000000000000000000000000011b6b79503fb875d",
                        "logIndex": "0x1",
                        "topics": [
                            "0x"+'0'*64
                        ],
                        "removed":False
                    }],
                'logsBloom': "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            }
            if 'to' in receipt:
                result['to'] = receipt['to']
            if 'contractAddress' in receipt:
                result['contractAddress'] = receipt['contractAddress']

            resp = {'jsonrpc':'2.0', 'result': result, 'id': rpc_id}

        # elif req.get('method') == 'eth_getCode':
        #     address = web3.Web3.toChecksumAddress(req['params'][0])
        #     block_height = req['params'][1]
        #     if block_height == 'latest':
        #         block_height = latest_block_number

        #     resp = {'jsonrpc':'2.0', 'result': '0x', 'id': rpc_id}

        elif req.get('method') == 'eth_gasPrice':
            resp = {'jsonrpc':'2.0', 'result': '0x0', 'id': rpc_id}

        elif req.get('method') == 'eth_estimateGas':
            resp = {'jsonrpc':'2.0', 'result': '0x5208', 'id': rpc_id}

        elif req.get('method') == 'eth_getTransactionCount':
            address = web3.Web3.toChecksumAddress(req['params'][0]).lower()
            accounts.setdefault(address, 0)
            count = accounts[address]
            print('eth_getTransactionCount', address, count)
            # yield tornado.gen.sleep(1)

            resp = {'jsonrpc':'2.0', 'result': hex(count), 'id': rpc_id}
            print('eth_getTransactionCount', resp)

        elif req.get('method') == 'eth_getBlockByHash':
            block_hash = req['params'][0].replace('0x', '')
            # k = 'blockhash-%s' % block_hash
            # block_json = conn.get(k.encode('utf8'))
            # print(block_json)
            # block = json.loads(block_json)
            resp = {'jsonrpc':'2.0', 'result': block, 'id': rpc_id}

        elif req.get('method') == 'eth_getTransactionByHash':
            transaction_hash = req['params'][0].replace('0x', '').lower()
            print(transaction_hash)
            # k = 'transaction-%s' % transaction_hash
            # while True:
            #     transaction_json = conn.get(k.encode('utf8'))
            #     print(transaction_json)
            #     try:
            #         transaction = json.loads(transaction_json)
            #         break
            #     except:
            #         yield tornado.gen.sleep(1)
            transaction = transactions.get(transaction_hash)

            resp = {'jsonrpc':'2.0', 'result': transaction, 'id': rpc_id}

        elif req.get('method') == 'eth_sendTransaction':
            transaction = req['params'][0]
            sender = transaction['from']
            tx_from = web3.Web3.toChecksumAddress(sender).lower()
            tx_nonce = int(transaction['nonce'], 16)
            gas_price = transaction['gasPrice']
            gas = transaction['gas']
            to = transaction['to']
            value = transaction['value']
            data = transaction['data'].replace('0x', '')
            chain_id = 0
            tx_list = [tx_nonce, gas_price, gas, to, value, data, chain_id]

            count = accounts.get(tx_from, 0)
            print('count', count, 'tx_nonce', tx_nonce)
            assert tx_nonce == count

            print('tx_from', tx_from)
            tx_hash = hashlib.sha256((tx_from + str(tx_nonce)).encode('utf8')).digest()
            print('txhash', tx_hash.hex())
            blocks[latest_block_number] = tx_hash.hex().replace('0x', '')
            transactions[tx_hash.hex().replace('0x', '')] = {
                'blockNumber': latest_block_number,
                'block_hash': tx_hash.hex().replace('0x', ''),
                'from': tx_from,
                'input': '0x'+data,
                'value': value,
                'gas': gas,
                'nonce': tx_nonce,
                'tx': tx_list
            }
            # transaction_queue.append((tx_hash, tx_from, tx_list))
            # yield tornado.gen.sleep(5)
            accounts[tx_from] = count + 1
            latest_block_number += 1
            resp = {'jsonrpc':'2.0', 'result': '%s' % tx_hash.hex(), 'id': rpc_id}

        elif req.get('method') == 'eth_sendRawTransaction':
            raw_tx = req['params'][0]
            print('raw_tx', raw_tx)
            # tx, tx_from, tx_to, _tx_hash = tx_info(raw_tx)
            # print('nonce', tx.nonce)
            raw_tx_bytes = binascii.unhexlify(raw_tx[2:])
            tx_list, vrs = eth_rlp2list(raw_tx_bytes)
            print('eth_rlp2list', tx_list, vrs)
            if len(tx_list) == 8:
                assert tx_list[0] == CHAIN_ID
                tx = eth_account._utils.typed_transactions.DynamicFeeTransaction.from_bytes(hexbytes.HexBytes(raw_tx_bytes))
                # tx = eth_account._utils.typed_transactions.TypedTransaction(transaction_type=2, transaction=tx)
                tx_hash = tx.hash()
                vrs = tx.vrs()
                tx_to = web3.Web3.toChecksumAddress(tx.as_dict()['to']).lower()
                tx_data = web3.Web3.to_hex(tx.as_dict()['data'])
                tx_nonce = web3.Web3.to_int(tx.as_dict()['nonce'])
            else:
                assert tx_list[6] == CHAIN_ID
                tx = eth_account._utils.legacy_transactions.Transaction.from_bytes(raw_tx_bytes)
                tx_hash = eth_account._utils.signing.hash_of_signed_transaction(tx)
                vrs = eth_account._utils.legacy_transactions.vrs_from(tx)
                tx_to = web3.Web3.toChecksumAddress(tx.to).lower()
                tx_data = web3.Web3.to_hex(tx.data)
                tx_nonce = tx.nonce

            tx_from = eth_account.Account._recover_hash(tx_hash, vrs=vrs).lower()
            # url = f"http://127.0.0.1:{setting.INDEXER_PORT}/entry?addr={tx_from}"
            # http_client = tornado.httpclient.AsyncHTTPClient()
            # response = yield http_client.fetch(url)
            # data = json.loads(response.body)
            data = {'entry': True, 'credit': 1000000000000000000}
            print(data)
            if not data['entry']:
                resp = {'jsonrpc':'2.0', 'error': {
                            			    "code": -32000,
			                                "message": "Not enough PoW credit for POWid to access chain"
                		}, 'id': rpc_id}
            else:
                k = 'account-%s-' % tx_from
                count = 0
                it = conn.iteritems()
                it.seek(k.encode('utf8'))
                for key, value_json in it:
                    # print(key)
                    if not key.startswith(k.encode('utf8')):
                        break

                    _, _, reverse_count = key.decode('utf8').split('-')
                    count = REVERSED_NO - int(reverse_count)
                    break
                # print('tx_nonce', tx_nonce, 'count', count)
                assert tx_nonce == count
                print('tx_from', tx_from, 'tx_nonce', tx_nonce)
                
                k = 'account-%s-%s' % (tx_from, str(REVERSED_NO - (tx_nonce+1)).zfill(16))
                conn.put(k.encode('utf8'), raw_tx_bytes)

                print('raw tx', tx_hash.hex())
                transaction_queue.append((tx_hash, tx_from, tx_list))
                resp = {'jsonrpc':'2.0', 'result': '%s' % tx_hash.hex(), 'id': rpc_id}

        elif req.get('method') == 'eth_newBlockFilter':
            filter_id = hex(random.randint(0x10000000000000000000000000000000000000000000, 0xffffffffffffffffffffffffffffffffffffffffffff))
            block_filters[filter_id] = latest_block_number
            resp = {'jsonrpc':'2.0', 'result': filter_id, 'id': rpc_id}

        elif req.get('method') == 'eth_getFilterChanges':
            filter_id = req['params'][0]
            #print('block_filters', block_filters)
            from_block_number = block_filters.get(filter_id)
            block_filters[filter_id] = latest_block_number

            block_hashes = []
            if from_block_number:
                it = conn.iteritems()
                k = 'blockno-'
                it.seek(k.encode('utf8'))
                for key, value_json in it:
                    if not key.startswith('blockno-'.encode('utf8')):
                        break

                    _, reverse_block_number, block_hash = key.decode('utf8').split('-')
                    block_number = REVERSED_NO - int(reverse_block_number)
                    if block_number == from_block_number:
                        break
                    block_hashes.insert(0, '0x'+block_hash)

            resp = {'jsonrpc':'2.0', 'result': block_hashes, 'id': rpc_id}

        elif req.get('method') == 'eth_accounts':
            local_accounts = []
            for i in range(10):
                account = web3.Account.from_key(hashlib.sha256(('brownie%s' % i).encode('utf8')).digest())
                local_accounts.append(account.address)

            resp = {'jsonrpc':'2.0', 'result': local_accounts, 'id': rpc_id}

        elif req.get('method') == 'web3_clientVersion':
            resp = {'jsonrpc':'2.0', 'result': 'geth', 'id': rpc_id}

        elif req.get('method') == 'net_version':
            resp = {'jsonrpc':'2.0', 'result': hex(CHAIN_ID),'id': rpc_id}

        elif req.get('method') == 'evm_snapshot':
            resp = {'jsonrpc':'2.0', 'result': hex(1),'id': rpc_id}

        elif req.get('method') == 'evm_increaseTime':
            resp = {'jsonrpc':'2.0', 'result': 1,'id': rpc_id}

        elif req.get('method') == 'eth_call':
            resp = {'jsonrpc':'2.0', 'result': 1,'id': rpc_id}

        elif req.get('method') == 'eth_getCode':
            resp = {'jsonrpc':'2.0', 'result': '0x','id': rpc_id}

        # print(resp)
        self.write(tornado.escape.json_encode(resp))

# def schedule():
#     global latest_block_number
#     global latest_block_hash
#     global transaction_queue

#     if not transaction_queue:
#         return

#     latest_block_number += 1
#     # print('block', latest_block_number)
#     block_hash = hashlib.sha256(latest_block_hash)
#     for tx_hash, tx_from, tx_list in transaction_queue:
#         print('tx_hash', tx_hash.hex())
#         block_hash.update(tx_hash)

#     for tx_hash, tx_from, tx_list in transaction_queue:
#         if len(tx_list) == 8:
#             data = tx_list[7]
#             nonce = tx_list[1]
#         else:
#             data = tx_list[5]
#             nonce = tx_list[0]

#         k = 'transaction-%s' % (tx_hash.hex().replace('0x', ''), )
#         print('k', k)
#         # print('tx', tx_list)
#         # print('tx nonce', nonce)
#         tx_json = {
#             'blockNumber': latest_block_number,
#             'block_hash': block_hash.hexdigest(),
#             'from': tx_from,
#             'input': '0x'+data,
#             'value': 0,
#             'gas': 1,
#             'nonce': nonce,
#             'tx': tx_list
#         }
#         conn.put(k.encode('utf8'), json.dumps(tx_json).encode('utf8'))

#     latest_block_hash = block_hash.digest()
#     block_json = {'number': latest_block_number, 'hash': block_hash.hexdigest(), 'transactions': [i[0].hex() for i in transaction_queue], 'timestamp': hex(int(time.time()))}
#     k = 'blockno-%s-%s' % (str(REVERSED_NO - latest_block_number).zfill(16), block_hash.hexdigest(), )
#     conn.put(k.encode('utf8'), json.dumps(block_json).encode('utf8'))
#     k = 'blockhash-%s' % (block_hash.hexdigest(), )
#     conn.put(k.encode('utf8'), json.dumps(block_json).encode('utf8'))
#     transaction_queue = []

# def main():
#     server = Application()
#     server.listen(setting.CTO_CHAIN_PORT, '0.0.0.0')
#     scheduler = tornado.ioloop.PeriodicCallback(schedule, 1000)
#     scheduler.start()
#     tornado.ioloop.IOLoop.instance().start()

# if __name__ == '__main__':
#     print(welcome_message)
#     main()

