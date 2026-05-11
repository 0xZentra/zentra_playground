import random
import time

import setting
from test_rpc_init import transaction, next_block

if __name__ == '__main__':
    accounts = setting.accounts

    while True:
        price = random.randint(300, 800)
        amount = 1 * 10**18
        call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", -{amount}, "USDC", {price * 10**6}]}}'
        print(f'Sell Limit: price={price}, amount={amount // 10**18}')
        tx_hash = transaction(accounts[0], call)
        print(f'  tx: {tx_hash}')

        quote = price * amount * (10**6) // (10**18)
        call = f'{{"p": "zen", "f": "trade_limit_order", "a": ["BTC", {amount}, "USDC", -{quote}]}}'
        print(f'Buy Limit:  price={price}, amount={amount // 10**18}')
        tx_hash = transaction(accounts[0], call)
        print(f'  tx: {tx_hash}')

        next_block()
        time.sleep(5)