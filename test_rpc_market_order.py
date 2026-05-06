import sys
import hashlib
import json

import web3

import setting

from test_rpc_init import *
from setting import accounts

if __name__ == '__main__':
    account_index = int(sys.argv[1])
    print(account_index, accounts[account_index].address.lower())
    btc_value = None if sys.argv[2] == 'none' else int(float(sys.argv[2])*10**18)
    print(btc_value)
    usdc_value = None if sys.argv[3] == 'none' else int(float(sys.argv[3])*10**6)
    print(usdc_value)

    call = {"p": "zen", "f": "trade_market_order", "a": ["BTC", btc_value, "USDC", usdc_value]}
    print(call)
    call_json = json.dumps(call)
    tx_hash = transaction(accounts[account_index], call_json)
    print(tx_hash)

    print('=== next block ===')
    next_block()