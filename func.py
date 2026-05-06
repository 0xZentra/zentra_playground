import os
import hashlib
import string
import json
import binascii
import importlib.util
import importlib.machinery

import web3
try:
    from eth_utils import keccak
except ImportError:
    keccak = None

import space

class NamedFunction:
    def __init__(self, f, name):
        self.f = f
        self.name = name

    def __call__(self, *args):
        a = list(args)
        if space.sender is None:
            raise Exception('sender is not set')
        r = self.f({'sender': space.sender}, {'p': 'zen', 'a': a, 'f': self.name})
        return r

    def __str__(self):
        return self.f.__str__()

    def __repr__(self):
        return self.f.__repr__()

def get_block_number():
    return space.latest_block_number

def set_sender(sender):
    space.sender = sender.lower()
    namespace['sender'] = space.sender


accounts = []
for i in range(10):
    private_key = hashlib.sha256(('brownie%s' % i).encode('utf8')).digest()
    account = web3.Account.from_key(private_key)
    accounts.append(account.address.lower())

namespace = {
    'put': space.put,
    'get': space.get, 
    'blocknumber': get_block_number,
    'nextblock': space.nextblock,
    'setsender': set_sender,
    'states': space.states,
    'sender': space.sender,
    'accounts': accounts,
    'a': accounts,
    '__name__': '__console__',
    '__doc__': None,
    'blocks': space.blocks,
    'events': space.events,
    'transactions': space.transactions,
    'nonces': space.nonces,
}


def load_all_zips():
    funcs_dir = os.path.join(os.path.dirname(__file__), 'funcs')
    if not os.path.exists(funcs_dir):
        print(f"Warning: {funcs_dir} not found.")
        return
    for filename in os.listdir(funcs_dir):
        if not filename.endswith('.py') or filename == '__init__.py':
            continue
        logic_path = os.path.join(funcs_dir, filename)
        module_name = f'funcs_{filename[:-3]}'
        loader = importlib.machinery.SourceFileLoader(module_name, logic_path)
        spec = importlib.util.spec_from_loader(module_name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)

        mod.get = space.get
        mod.put = space.put
        mod.event = space.event
        mod.handle_lookup = space.handle_lookup
        mod.hashlib = hashlib
        mod.string = string
        mod.json = json
        mod.binascii = binascii
        if keccak:
            mod.keccak = keccak

        for attr in dir(mod):
            if attr in ['put', 'get', 'event', 'handle_lookup']:
                continue
            if attr.startswith('_'):
                continue
            func = getattr(mod, attr)
            if callable(func):
                # print(attr)
                wrapped = NamedFunction(func, attr)
                namespace[attr] = wrapped
