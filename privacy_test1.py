import space
import funcs
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak
from typing import ChainMap

# Setup
space.states = [{}]

def sign_message(msg, private_key):
    encoded_msg = encode_defunct(primitive=keccak(text=msg))
    signed = Account.sign_message(encoded_msg, private_key)
    signature = signed.signature.hex()
    if not signature.startswith('0x'):
        signature = '0x' + signature
    return signature

def print_merged_state():
    merged_state = dict(ChainMap(*reversed(space.states)))
    print("\n--- Current Merged State ---")
    for k in sorted(merged_state.keys()):
        print(f"{k}: {merged_state[k]}")
    print("---------------------------\n")

try:
    # 1. Create original asset and token
    print("Step 1: Creating asset and token...")
    funcs.asset_create({'sender':'0x001'}, {'p': 'zen', 'f': 'asset_create', 'a':['USDT']})
    space.nextblock()
    funcs.token_create({'sender':'0x001'}, {'p': 'zen', 'f': 'token_create', 'a':['USDT', 'Tether', 6]})
    space.nextblock()
    funcs.token_mint_once({'sender':'0x001'}, {'p': 'zen', 'f': 'token_mint_once', 'a':['USDT', 10000]})
    space.nextblock()

    # 2. Initialize Privacy
    print("Step 2: Initializing privacy...")
    # Provider account
    provider_key = "0x" + "1" * 64
    provider_account = Account.from_key(provider_key)
    provider_addr = provider_account.address.lower()
    print(f"Provider address: {provider_addr}")

    paillier_pub = 123456789 # Mock Paillier N
    paillier_n2 = paillier_pub * paillier_pub

    funcs.privacy_init({'sender': provider_addr}, {
        'p': 'zen', 
        'f': 'privacy_init', 
        'a': ['USDT', 'USDT_P', provider_addr, str(paillier_pub)]
    })
    space.nextblock()

    # Setup permissions for USDT_P
    funcs.asset_create({'sender': provider_addr}, {'p': 'zen', 'f': 'asset_create', 'a':['USDT_P']})
    space.nextblock()
    funcs.asset_update_functions({'sender': provider_addr}, {
        'p': 'zen', 
        'f': 'asset_update_functions', 
        'a': ['USDT_P', ['privacy_deposit', 'privacy_withdraw', 'privacy_init', 'token_transfer']]
    })
    space.nextblock()

    # Setup permissions for USDT
    funcs.asset_update_functions({'sender': '0x001'}, {
        'p': 'zen', 
        'f': 'asset_update_functions', 
        'a': ['USDT', ['token_transfer', 'token_mint_once', 'privacy_deposit']]
    })
    space.nextblock()

    # 3. Privacy Deposit
    print("Step 3: Depositing into privacy...")
    user_addr = '0x001'
    amount = 1000
    # amount_cipher = (1 + m*n) % n^2 (Simplified Paillier for testing)
    amount_cipher = (1 + amount * paillier_pub) % paillier_n2
    nonce = 1

    msg_to_sign = f'USDT_P,privacy_deposit,{str(amount)},{str(amount_cipher)},{str(nonce)}'
    signature = sign_message(msg_to_sign, provider_key)

    funcs.privacy_deposit({'sender': user_addr}, {
        'p': 'zen', 
        'f': 'privacy_deposit', 
        'a': ['USDT_P', amount, amount_cipher, nonce, signature]
    })
    space.nextblock()
    print("Deposit successful.")

    # 4. Privacy Withdraw
    print("Step 4: Withdrawing from privacy...")
    withdraw_amount = 400
    withdraw_amount_cipher = (1 + withdraw_amount * paillier_pub) % paillier_n2
    old_balance_cipher = amount_cipher # Since it was the first deposit
    withdraw_nonce = 2 # Previous nonce for 0x001 was 1

    msg_to_sign_withdraw = f"USDT_P,privacy_withdraw,{user_addr},{withdraw_nonce},{withdraw_amount},{withdraw_amount_cipher},{old_balance_cipher}"
    signature_withdraw = sign_message(msg_to_sign_withdraw, provider_key)

    funcs.privacy_withdraw({'sender': user_addr}, {
        'p': 'zen', 
        'f': 'privacy_withdraw', 
        'a': ['USDT_P', withdraw_amount, withdraw_amount_cipher, old_balance_cipher, withdraw_nonce, signature_withdraw]
    })
    space.nextblock()
    print("Withdraw successful.")

    print_merged_state()

except Exception as e:
    print(f"Test failed with error: {e}")
    import traceback
    traceback.print_exc()


