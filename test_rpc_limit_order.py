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
    btc_value = float(sys.argv[2])
    print(btc_value)
    usdc_value = float(sys.argv[3])
    print(usdc_value)
    call = {"p": "zen", "f": "trade_limit_order", "a": ["BTC", int(btc_value*10**18), "USDC", int(usdc_value*10**6)]}
    print(call)
    call_json = json.dumps(call)
    tx_hash = transaction(accounts[account_index], call_json)
    print(tx_hash)

    print('=== next block ===')
    next_block()