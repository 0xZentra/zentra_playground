import space
from play import GLOBAL_FUNCTIONS

def call_zip(name, sender, args_list):
    func = GLOBAL_FUNCTIONS[name]
    info = {'sender': sender}
    req = {'p': 'zen', 'f': name, 'a': args_list}
    return func(info, req)

import secrets
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak
from typing import ChainMap

p = 8748842099960345447313630731652402805516069630214453405766470733643016240435346922524211494453926395208032094452365616184409998123133054345264908686154801
q = 10913953225111233777133529790235905042422493716528276624132211524892437175805771347582813666552903184682738196471955281855703803211165613888365016421534109
n = 95484453452851151319146099534921060730772215626135961163491913912336477811863582609045983397814414269633849494288732608649821900304800972834742168506707143630327145078886467708821477118434659068956432905871648234970891021733879791975265673569299171364659623036654115772969795595800647152283420826440675607309
g = 95484453452851151319146099534921060730772215626135961163491913912336477811863582609045983397814414269633849494288732608649821900304800972834742168506707143630327145078886467708821477118434659068956432905871648234970891021733879791975265673569299171364659623036654115772969795595800647152283420826440675607310


def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a

def egcd(a, b):
    x0, y0 = 1, 0
    x1, y1 = 0, 1
    while b != 0:
        q = a // b
        a, b = b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    return a, x0, y0

def modinv(a, n):
    g, x, _ = egcd(a, n)
    if g != 1:
        raise ValueError("no modular inverse")
    return x % n

def lcm(a, b):
    return a // gcd(a, b) * b


paillier_public_key = (n, g)
# paillier_private_key = (p, q)
lam = lcm(p - 1, q - 1)
# g = n + 1, so L(g^lam mod n^2) = lam
# thus mu = modinv(lam, n)
mu = modinv(lam, n)

paillier_private_key = (lam, mu)

def encrypt(pub, m):
    n, g = pub
    if not (0 <= m < n):
       raise ValueError("message out of range")
    n2 = n * n
    while True:
        r = secrets.randbelow(n)
        if r > 0 and gcd(r, n) == 1:
            break
    c1 = pow(g, m, n2)
    c2 = pow(r, n, n2)
    return (c1 * c2) % n2


def decrypt(pub, priv, c):
    n, g = pub
    lam, mu = priv
    n2 = n * n
    if not (0 <= c < n2):
        raise ValueError("ciphertext out of range")
    x = pow(c, lam, n2)
    l_val = (x - 1) // n
    return (l_val * mu) % n

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
    return merged_state

try:
    # 1. Create original asset and token
    print("Step 1: Creating asset and token...")
    call_zip('asset_create', '0x001', ['USDT'])
    space.nextblock()
    call_zip('token_create', '0x001', ['USDT', 'Tether', 6])
    space.nextblock()
    call_zip('token_mint_once', '0x001', ['USDT', 10000])
    space.nextblock()
    print_merged_state()

    # 2. Initialize Privacy
    print("Step 2: Initializing privacy...")
    # Provider account
    provider_key = "0x" + "1" * 64
    provider_account = Account.from_key(provider_key)
    provider_addr = provider_account.address.lower()
    print(f"Provider address: {provider_addr}")

    # paillier_pub = 123456789 # Mock Paillier N
    # paillier_n2 = paillier_pub * paillier_pub

    call_zip('privacy_init', provider_addr, ['USDT', 'USDT_P', provider_addr, str(paillier_public_key[0])])
    space.nextblock()

    # Setup permissions for USDT_P
    call_zip('asset_create', provider_addr, ['USDT_P'])
    space.nextblock()
    call_zip('asset_update_functions', provider_addr, ['USDT_P', ['privacy_deposit', 'privacy_withdraw', 'privacy_init', 'token_transfer', 'privacy_transfer']])
    space.nextblock()

    # Setup permissions for USDT
    call_zip('asset_update_functions', '0x001', ['USDT', ['token_transfer', 'token_mint_once', 'privacy_deposit']])
    space.nextblock()
    print_merged_state()

    # 3. Privacy Deposit
    print("Step 3: Depositing into privacy...")
    user_addr = '0x001'
    amount = 1000
    amount_cipher = encrypt(paillier_public_key, int(amount))
    # print(decrypt(paillier_public_key, paillier_private_key, amount_cipher))
    nonce = 1

    msg_to_sign = f'USDT_P,privacy_deposit,{str(amount)},{str(amount_cipher)},{str(nonce)}'
    signature = sign_message(msg_to_sign, provider_key)

    call_zip('privacy_deposit', user_addr, ['USDT_P', amount, amount_cipher, nonce, signature])
    space.nextblock()
    print("Deposit successful.")
    print_merged_state()

    # 4. Privacy Withdraw
    print("Step 4: Withdrawing from privacy...")
    withdraw_amount = 400
    withdraw_amount_cipher = encrypt(paillier_public_key, int(withdraw_amount))

    old_balance_cipher = amount_cipher # Since it was the first deposit
    withdraw_nonce = 2 # Previous nonce for 0x001 was 1

    msg_to_sign_withdraw = f"USDT_P,privacy_withdraw,{user_addr},{withdraw_nonce},{withdraw_amount},{withdraw_amount_cipher},{old_balance_cipher}"
    signature_withdraw = sign_message(msg_to_sign_withdraw, provider_key)

    call_zip('privacy_withdraw', user_addr, ['USDT_P', withdraw_amount, withdraw_amount_cipher, old_balance_cipher, withdraw_nonce, signature_withdraw])
    space.nextblock()
    print("Withdraw successful.")
    print_merged_state()

    # 5. Privacy Transfer
    print("Step 5: Transferring within privacy...")
    receiver_addr = '0x002'
    transfer_amount = 200
    transfer_nonce = 3
    transfer_amount_cipher = encrypt(paillier_public_key, int(transfer_amount))
    msg_to_sign_transfer = f"USDT_P,privacy_transfer,{user_addr},{receiver_addr},{transfer_nonce},{transfer_amount_cipher}"
    signature_transfer = sign_message(msg_to_sign_transfer, provider_key)
    transfer_args = [
        'USDT_P',
        receiver_addr,
        transfer_amount_cipher,
        transfer_nonce,
        signature_transfer
    ]
    call_zip('privacy_transfer', user_addr, transfer_args)
    space.nextblock()
    print("Transfer successful")
    state = print_merged_state()

    encrypted_val = state['USDT_P-privacy_balance:0x001'][1]
    decoded_val = decrypt(paillier_public_key,
                    paillier_private_key,
                    encrypted_val)
    # print(f"Encrypted balance for 0x001: {encrypted_val}")
    print(f"Decoded balance for 0x001: {decoded_val}")

    encrypted_val = state['USDT_P-privacy_balance:0x002'][1]
    decoded_val = decrypt(paillier_public_key,
                    paillier_private_key,
                    encrypted_val)
    # print(f"Encrypted balance for 0x002: {encrypted_val}")
    print(f"Decoded balance for 0x002: {decoded_val}")

except Exception as e:
    print(f"Test failed with error: {e}")
    import traceback
    traceback.print_exc()