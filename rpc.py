# from __future__ import print_function
import sys
import os

import random
import hashlib
import json
import binascii
# import time
# import pathlib

import tornado.web
import tornado.gen
import tornado.escape

import web3
from eth_account.typed_transactions import TypedTransaction
from eth_account._utils.legacy_transactions import Transaction as LegacyTransaction, vrs_from
from eth_account._utils.signing import extract_chain_id
from eth_account import Account
import hexbytes
import rlp

import space
import func
from space import broadcast

CHAIN_ID = 31337
REVERSED_NO = 10**16

try:
    web3.Web3.toChecksumAddress = web3.Web3.to_checksum_address
except:
    pass


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
        chain_id, chain_naive_v = extract_chain_id(v)
        v_standard = chain_naive_v - V_OFFSET
        return [nonce, gas_price, gas, to, value, data, chain_id], [v_standard, r, s]

welcome_message = '''Chain id: %s<br>
RPC: http://127.0.0.1:8545<br>
<a href="http://127.0.0.1:8545/static/call.html">Func call demo</a><br>
<br>
pip install eth-brownie<br>
brownie console<br>
<br>
cast<br>
''' % (CHAIN_ID)
for i in range(10):
    private_key = hashlib.sha256(('brownie%s' % i).encode('utf8')).digest()
    account = web3.Account.from_key(private_key)
    welcome_message += f'{account.address} < 0x{private_key.hex()}<br>'

# HTTP_PROXY=127.0.0.1:7890 brownie console --network playground
# brownie console --network hardhat

class RPCHandler(tornado.web.RequestHandler):
    def get(self):
        self.finish(welcome_message)

    @tornado.gen.coroutine
    def post(self):
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

        if req.get('method') == 'zentra_nextBlock':
            space.nextblock()
            resp = {'jsonrpc': '2.0', 'result': hex(space.latest_block_number), 'id': rpc_id}
            self.write(tornado.escape.json_encode(resp))
            return

        if req.get('method') == 'eth_chainId':
            resp = {'jsonrpc':'2.0', 'result': hex(CHAIN_ID), 'id':rpc_id}

        elif req.get('method') == 'eth_blockNumber':
            block_number = space.latest_block_number
            resp = {'jsonrpc':'2.0', 'result': hex(block_number), 'id':rpc_id}

        elif req.get('method') == 'eth_getBlockByNumber':
            block_number = req['params'][0]
            if block_number == 'latest':
                block_number = space.latest_block_number
            else:
                block_number = int(block_number, 16)

            # 获取 block hash
            block_hash = space.block_hashes.get(block_number)
            if not block_hash:
                # 如果还没初始化，返回 null
                result = None
                resp = {'jsonrpc':'2.0', 'result': result, 'id':rpc_id}
                self.write(tornado.escape.json_encode(resp))
                return
            print('eth_getBlockByNumber', block_number, block_hash)

            result = {
                'number': hex(block_number),
                'hash': '0x' + block_hash,
                'timestamp': '0x0',
                'gasLimit': '0x1c9c380'
            }

            resp = {'jsonrpc':'2.0', 'result': result, 'id':rpc_id}

        elif req.get('method') == 'eth_getBalance':
            address = web3.Web3.toChecksumAddress(req['params'][0])
            block_height = req['params'][1]
            if block_height == 'latest':
                block_height = space.latest_block_number

            resp = {'jsonrpc':'2.0', 'result': hex(1000000000000000000), 'id':rpc_id}

        elif req.get('method') == 'eth_getTransactionReceipt':
            transaction_hash = req['params'][0]
            print(transaction_hash)
            # receipt_json = receipts_tree[transaction_hash.replace('0x', '').encode('utf8')]
            # transaction_json = conn.get(('transaction-%s' % transaction_hash.replace('0x', '')).encode('utf8'))
            # receipt = json.loads(transaction_json)
            print('space.transactions', space.transactions)
            receipt = space.transactions.get(transaction_hash.replace('0x', '').lower())
            print('receipt', receipt)
            if receipt is None:
                resp = {'jsonrpc':'2.0', 'result': None, 'id': rpc_id}

            else:
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

        elif req.get('method') == 'eth_gasPrice':
            resp = {'jsonrpc':'2.0', 'result': '0x0', 'id': rpc_id}

        elif req.get('method') == 'eth_estimateGas':
            resp = {'jsonrpc':'2.0', 'result': '0x5208', 'id': rpc_id}

        elif req.get('method') == 'eth_getTransactionCount':
            address = web3.Web3.toChecksumAddress(req['params'][0]).lower()
            space.nonces.setdefault(address, 0)
            count = space.nonces[address]
            print('eth_getTransactionCount', address, count)
            # yield tornado.gen.sleep(1)

            resp = {'jsonrpc':'2.0', 'result': hex(count), 'id': rpc_id}
            print('eth_getTransactionCount', resp)

        elif req.get('method') == 'eth_getBlockByHash':
            block_hash = req['params'][0].replace('0x', '')
            block_number = None
            for bn, bh in space.block_hashes.items():
                if bh == block_hash:
                    block_number = bn
                    break

            if block_number is None:
                result = None
            else:
                result = {
                    'number': hex(block_number),
                    'hash': '0x' + block_hash,
                    'timestamp': '0x0',
                    'gasLimit': '0x1c9c380'
                }
            resp = {'jsonrpc':'2.0', 'result': result, 'id': rpc_id}

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
            transaction = space.transactions.get(transaction_hash)

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

            count = space.nonces.get(tx_from, 0)
            print('count', count, 'tx_nonce', tx_nonce)
            assert tx_nonce == count

            print('tx_from', tx_from)
            tx_hash = hashlib.sha256((tx_from + str(tx_nonce)).encode('utf8')).digest()
            print('txhash', tx_hash.hex())
            
            # Record transaction to current block
            block_hash = space.block_hashes.get(space.latest_block_number)
            if not block_hash:
                import random
                import string
                block_hash = ''.join(random.choices(string.hexdigits.lower(), k=64))
                space.block_hashes[space.latest_block_number] = block_hash
            
            if space.latest_block_number not in space.blocks:
                space.blocks[space.latest_block_number] = []
            space.blocks[space.latest_block_number].append(tx_hash.hex().replace('0x', ''))
            
            space.transactions[tx_hash.hex().replace('0x', '')] = {
                'blockNumber': space.latest_block_number,
                'block_hash': block_hash,
                'from': tx_from,
                'input': '0x'+data,
                'value': value,
                'gas': gas,
                'nonce': tx_nonce,
                'tx': tx_list
            }

            space.nonces[tx_from] = count + 1

            try:
                data_bytes = binascii.unhexlify(data)
                data_json = json.loads(data_bytes.decode('utf-8'))
                print('parsed_json', data_json)
                func.set_sender(tx_from)
                func.namespace[data_json['f']](*data_json['a'])
                print('=== function executed, events now:', len(space.events), '===')

                # Broadcast trade events via WS
                if data_json.get('f') in ['trade_limit_order', 'trade_market_order']:
                    blk_num = space.latest_block_number
                    if blk_num in space.events:
                        for evt in space.events[blk_num]:
                            if evt['event'] in ['TradeLimitTake', 'TradeMarketTake']:
                                evt_args = evt['args']
                                if len(evt_args) >= 5:
                                    pair = evt_args[0]
                                    parts = pair.split('_')
                                    if len(parts) == 2:
                                        base, quote = parts
                                        trade_msg = json.dumps({
                                            'type': 'trade',
                                            'timestamp': space.block_times.get(blk_num, int(__import__('time').time())),
                                            'price': evt_args[4] / (10**6),
                                            'amount': evt_args[3] / (10**18),
                                            'side': evt_args[1],
                                            'pair': pair
                                        })
                                        broadcast(trade_msg)

            except Exception as e:
                import traceback
                traceback.print_exc()
                print('failed to execute function:', e)

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
                tx = TypedTransaction.from_bytes(hexbytes.HexBytes(raw_tx_bytes))
                tx_hash = tx.hash()
                vrs = tx.vrs()
                tx_to = web3.Web3.toChecksumAddress(tx.as_dict()['to']).lower()
                tx_data = web3.Web3.to_hex(tx.as_dict()['data'])
                tx_nonce = web3.Web3.to_int(tx.as_dict()['nonce'])
            else:
                assert tx_list[6] == CHAIN_ID
                tx = LegacyTransaction.from_bytes(raw_tx_bytes)
                tx_hash = tx.hash()
                vrs = vrs_from(tx)
                tx_to = web3.Web3.toChecksumAddress(tx.to).lower()
                tx_data = web3.Web3.to_hex(tx.data)
                tx_nonce = tx.nonce

            tx_from = Account.recover_transaction(raw_tx).lower()
            count = space.nonces.get(tx_from, 0)
            print('tx_from', tx_from, 'tx_nonce', tx_nonce, 'count', count)
            assert tx_nonce == count

            tx_hash_hex = tx_hash.hex().replace('0x', '')
            block_hash = space.block_hashes.get(space.latest_block_number)
            if not block_hash:
                import random
                import string
                block_hash = ''.join(random.choices(string.hexdigits.lower(), k=64))
                space.block_hashes[space.latest_block_number] = block_hash
            
            if space.latest_block_number not in space.blocks:
                space.blocks[space.latest_block_number] = []
            space.blocks[space.latest_block_number].append(tx_hash_hex)

            space.transactions[tx_hash_hex] = {
                'blockNumber': space.latest_block_number,
                'block_hash': block_hash,
                'from': tx_from,
                'input': '0x' + tx_data.replace('0x', ''),
                'value': tx_list[3] if len(tx_list) > 3 else 0,
                'gas': tx_list[4] if len(tx_list) > 4 else 21000,
                'nonce': tx_nonce,
                'tx': tx_list
            }
            space.nonces[tx_from] = count + 1
            # No automatic nextblock - user must call it manually or via timer

            print('raw tx', tx_hash.hex())
            print('tx_data', tx_data)
            try:
                data_bytes = binascii.unhexlify(tx_data.replace('0x', ''))
                data_json = json.loads(data_bytes.decode('utf-8'))
                print('parsed_json', data_json)
                func.set_sender(tx_from)
                func.namespace[data_json['f']](*data_json['a'])
                print('=== function executed, events now:', len(space.events), '===')

                if data_json.get('f') in ['trade_limit_order', 'trade_market_order']:
                    blk_num = space.latest_block_number
                    if blk_num in space.events:
                        for evt in space.events[blk_num]:
                            if evt['event'] in ['TradeLimitTake', 'TradeMarketTake']:
                                evt_args = evt['args']
                                if len(evt_args) >= 5:
                                    pair = evt_args[0]
                                    parts = pair.split('_')
                                    if len(parts) == 2:
                                        trade_msg = json.dumps({
                                            'type': 'trade',
                                            'timestamp': space.block_times.get(blk_num, int(__import__('time').time())),
                                            'price': evt_args[4] / (10**6),
                                            'amount': evt_args[3] / (10**18),
                                            'side': evt_args[1],
                                            'pair': pair
                                        })
                                        broadcast(trade_msg)

            except Exception as e:
                import traceback
                traceback.print_exc()
                print('failed to execute function:', e)
            # transaction_queue.append((tx_hash, tx_from, tx_list))
            resp = {'jsonrpc':'2.0', 'result': '0x%s' % tx_hash.hex(), 'id': rpc_id}

        elif req.get('method') == 'eth_newBlockFilter':
            filter_id = hex(random.randint(0x10000000000000000000000000000000000000000000, 0xffffffffffffffffffffffffffffffffffffffffffff))
            block_filters[filter_id] = space.latest_block_number
            resp = {'jsonrpc':'2.0', 'result': filter_id, 'id': rpc_id}

        elif req.get('method') == 'eth_getFilterChanges':
            filter_id = req['params'][0]
            #print('block_filters', block_filters)
            from_block_number = block_filters.get(filter_id)
            block_filters[filter_id] = space.latest_block_number

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
                private_key = hashlib.sha256(('brownie%s' % i).encode('utf8')).digest()
                account = web3.Account.from_key(private_key)
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

        elif req.get('method') == 'eth_getStorageAt':
            print('eth_getStorageAt', req)
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

