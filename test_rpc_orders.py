import sys
import hashlib
import json
import random
import time

import requests
import web3

import setting
from test_rpc_init import transaction, next_block

if __name__ == '__main__':
    accounts = setting.accounts

    while True:
        price = random.randint(300, 800)
        amount = 1 * 10**18
        quote = price * 10**6
        call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", -{amount}, "USDC", {quote}]}}'
        print(f'Sell Limit: price={price}, amount={amount // 10**18}')
        tx_hash = transaction(accounts[0], call)
        print(f'  tx: {tx_hash}')

        quote = price * amount * (10**6) // (10**18)
        call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", {amount}, "USDC", -{quote}]}}'
        print(f'Buy Limit: price={price}, amount={amount // 10**18}')
        tx_hash = transaction(accounts[0], call)
        print(f'  tx: {tx_hash}')

        next_block()
        time.sleep(5)

    # # Block 1: 创建卖单挂单（价格 660, 670, 680，不成交）
    # print('=== 创建卖单挂单 ===')
    # for i in range(3):
    #     price = 660 + i * 10
    #     amount = 1 * 10**18
    #     quote = price * 10**6
    #     call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", -{amount}, "USDC", {quote}]}}'
    #     print(f'Sell Limit {i+1}: price={price}, amount={amount // 10**18}')
    #     print(f'  tx: {tx_hash}')

    # print('\n=== next block ===')

    # # Block 2: 创建买单挂单（价格 640, 630, 620，不成交）
    # print('=== 创建买单挂单 ===')
    # for i in range(3):
    #     price = 640 - i * 10
    #     amount = 1 * 10**18
    #     quote = price * 10**6
    #     call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", {amount}, "USDC", -{quote}]}}'
    #     print(f'Buy Limit {i+1}: price={price}, amount={amount // 10**18}')
    #     tx_hash = transaction(accounts[1], call)
    #     print(f'  tx: {tx_hash}')

    # print('\n=== next block ===')
    # next_block()

    # # Block 3: SELL Limit order，价格 620，低于买方最高价 640，会成交
    # print('=== Block 3: SELL Limit (成交) ===')
    # price = 620
    # amount = 1 * 10**18
    # quote = price * 10**6
    # call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", -{amount}, "USDC", {quote}]}}'
    # print(f'SELL Limit: price={price}, amount={amount // 10**18}')
    # tx_hash = transaction(accounts[2], call)
    # print(f'  tx: {tx_hash}')

    # print('\n=== next block ===')
    # next_block()

    # # Block 4: BUY Limit order，价格 670，高于卖方最低价 660，会成交
    # print('=== Block 4: BUY Limit (成交) ===')
    # price = 670
    # amount = 1 * 10**18
    # quote = price * 10**6
    # call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", {amount}, "USDC", -{quote}]}}'
    # print(f'BUY Limit: price={price}, amount={amount // 10**18}')
    # tx_hash = transaction(accounts[1], call)
    # print(f'  tx: {tx_hash}')

    # print('\n=== next block ===')
    # next_block()

    print('=== Market SELL ===')
    amount = 0.1 * 10**18
    call = f'{{"p": "zen", "f": "trade_market_order", "a": ["BTC", -{amount}, "USDC", null]}}'
    print(f'Market SELL: amount={amount // 10**18}')
    tx_hash = transaction(accounts[2], call)
    print(f'  tx: {tx_hash}')

    print('\n=== next block ===')
    next_block()

    print('=== Market BUY ===')
    amount = 100 * 10**6
    call = f'{{"p": "zen", "f": "trade_market_order", "a": ["BTC", null, "USDC", -{amount}]}}'
    print(f'Market BUY: amount={amount // 10**18}')
    tx_hash = transaction(accounts[0], call)
    print(f'  tx: {tx_hash}')

    print('\n=== next block ===')
    next_block()

    print('\n=== 完成 ===')