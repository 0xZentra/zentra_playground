import sys
import requests

import setting
import web3

PROVIDER_HOST = 'http://127.0.0.1:8545'

def get_balance(account_index):
    account = setting.accounts[account_index]
    addr = account.address.lower()

    tokens = {
        'USDC': 6,
        'BTC': 18,
    }
    balances = {}

    for token, decimals in tokens.items():
        resp = requests.get(f'{PROVIDER_HOST}/api/get_latest_state?prefix=base-{token}-balance:{addr}')
        data = resp.json()
        balance = data.get('result', '0')
        if balance and balance != '0':
            formatted = int(balance) / (10 ** decimals)
            balances[token] = formatted
        else:
            balances[token] = 0

    print(f'Account {account_index}: {addr}')
    for token, balance in balances.items():
        print(f'  {token}: {balance}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python test_get_balance.py <account_index>')
        print('Example: python test_get_balance.py 0')
        sys.exit(1)

    account_index = int(sys.argv[1])
    get_balance(account_index)