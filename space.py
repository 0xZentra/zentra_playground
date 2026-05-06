import random
import string

latest_block_number = 0
states = {}  # block_number -> {key: (addr, value)}
blocks = {}  # block_number -> [tx_hashes]
block_hashes = {}  # block_number -> block_hash
transactions = {}  # tx_hash -> tx
events = {}  # block_number -> [{event, args}, ...]
nonces = {}  # addr -> nonce

sender = None

block_mode = 0  # 0: manual, 1: auto after tx, >=2: auto with interval (seconds)
block_timer = None


def _gen_block_hash():
    return ''.join(random.choices(string.hexdigits.lower(), k=64))

def _init_block_mode():
    global block_mode, block_timer
    import setting
    import tornado.ioloop
    block_mode = setting.BLOCK_MODE
    if block_timer is not None:
        block_timer.stop()
        block_timer = None
    if block_mode >= 2:
        interval_ms = block_mode * 1000
        block_timer = tornado.ioloop.PeriodicCallback(nextblock, interval_ms)
        block_timer.start()
    # 初始化第一个 block
    # if latest_block_number == 0:
    #     block_hash = _gen_block_hash()
    #     blocks[latest_block_number] = []
    #     block_hashes[latest_block_number] = block_hash

def put(_owner, _asset, _var, _value, _key = None):
    global sender

    assert type(_var) is str
    if _key is not None:
        assert type(_key) is str
        var = '%s:%s' % (_var, _key)
    else:
        var = _var

    asset_name = _asset
    addr = _owner.lower()
    k = '%s-%s' % (asset_name, var)
    state = states.setdefault(latest_block_number, {})
    state[k] = addr, _value

def get(_asset, _var, _default = None, _key = None):
    global sender
    global states

    asset_name = _asset
    value = _default
    assert type(_var) is str
    if _key is not None:
        assert type(_key) is str
        var = '%s:%s' % (_var, _key)
    else:
        var = _var

    k = '%s-%s' % (asset_name, var)
    for block_num in sorted(states.keys(), reverse=True):
        state = states[block_num]
        if k in state:
            addr, v = state[k]
            return v, addr

    return value, None

def event(_event, _args):
    global states, latest_block_number
    if latest_block_number not in events:
        events[latest_block_number] = []
    events[latest_block_number].append({'event': _event, 'args': _args})

def handle_lookup(_addr):
    return _addr

def nextblock():
    global states
    global latest_block_number
    global blocks, block_hashes

    block_hash = _gen_block_hash()
    # blocks[latest_block_number] = []
    block_hashes[latest_block_number] = block_hash

    latest_block_number += 1
    states[latest_block_number] = {}

