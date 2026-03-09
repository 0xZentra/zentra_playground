

import code
import readline
import rlcompleter

import space
import funcs


space.states = [{}]


funcs.asset_create({'sender':'0x002'}, {'p': 'zen', 'f': 'asset_create', 'a':['USDT']})
# print(space.states[-1])
space.nextblock()

funcs.token_create({'sender':'0x002'}, {'p': 'zen', 'f': 'token_create', 'a':['USDT', 'mock', 6]})
# print(space.states[-1])
space.nextblock()

funcs.token_mint_once({'sender':'0x002'}, {'p': 'zen', 'f': 'token_mint_once', 'a':['USDT', 10000]})
# print(space.states[-1])
space.nextblock()


# funcs.token_transfer({'sender':'0x001'}, {'p': 'zen', 'f': 'token_transfer', 'a':['USDT', '0x002', 5000]})
# # print(space.states[-1])
# space.nextblock()

funcs.token_transfer({'sender':'0x002'}, {'p': 'zen', 'f': 'token_transfer', 'a':['USDT', '0x001', 5000]})
# print(space.states[-1])
space.nextblock()

from typing import ChainMap
merged_state = dict(ChainMap(*reversed(space.states)))
for k in merged_state:
    print(k, merged_state[k])
