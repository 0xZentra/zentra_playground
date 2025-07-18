import string
from inspect import currentframe, getframeinfo

from space import put, get, handle_lookup
import space

def token_mint_once(info, args): # pragma: no cover
    tick = args['a'][0]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

    value = int(args['a'][1])
    assert value > 0

    assert args['f'] == 'token_mint_once'
    # print(get('asset', 'functions', [], tick))
    assert args['f'] in get('asset', 'functions', [], tick)

    sender = info['sender']
    handle = handle_lookup(sender)
    addr = handle or sender
    total = int(args['a'][1])
    assert get(tick, 'total', None) is None
    put(addr, tick, 'total', total)

    balance = get(tick, 'balance', 0, addr)
    balance += value
    put(addr, tick, 'balance', balance, addr)

def token_mint(info, args): # pragma: no cover
    tick = args['a'][0]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

    assert args['f'] == 'token_mint'
    assert args['f'] in get('asset', 'functions', [], tick)

    value = int(args['a'][1])
    assert value > 0
    sender = info['sender']
    handle = handle_lookup(sender)
    addr = handle or sender

    balance = get(tick, 'balance', 0, addr)
    balance += value
    put(addr, tick, 'balance', balance, addr)

def token_create(info, args): # pragma: no cover
    assert args['f'] == 'token_create'
    sender = info['sender']
    handle = handle_lookup(sender)
    addr = handle or sender

    tick = args['a'][0]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

    name = args['a'][1]
    assert type(name) is str
    decimal = int(args['a'][2])
    assert type(decimal) is int
    assert decimal >= 0 and decimal <= 18

    functions = ['transfer', 'approve', 'transfer_from', 'token_mint_once', 'asset_update_ownership', 'asset_update_functions']
    put(addr, tick, 'name', name)
    put(addr, tick, 'decimal', decimal)
    put(addr, 'asset', 'functions', functions, tick)

def transfer(info, args): # pragma: no cover
    tick = args['a'][0]
    assert set(tick) <= set(string.ascii_uppercase+'_')

    assert args['f'] == 'transfer'
    assert args['f'] in get('asset', 'functions', [], tick)

    receiver = args['a'][1].lower()
    assert len(receiver) <= 42
    assert type(receiver) is str
    if len(receiver) == 42:
        assert receiver.startswith('0x')
        assert set(receiver[2:]) <= set(string.digits+'abcdef')
    else:
        assert len(receiver) > 4

    sender = info['sender']
    handle = handle_lookup(sender)
    addr = handle or sender

    value = int(args['a'][2])
    assert value > 0

    sender_balance = get(tick, 'balance', 0, addr)
    assert sender_balance >= value
    sender_balance -= value
    put(addr, tick, 'balance', sender_balance, addr)
    receiver_balance = get(tick, 'balance', 0, receiver)
    receiver_balance += value
    put(receiver, tick, 'balance', receiver_balance, receiver)

def asset_create(info, args): # pragma: no cover
    assert args['f'] == 'asset_create'
    sender = info['sender']
    tick = args['a'][0]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')
    handle = handle_lookup(sender)
    addr = handle or sender
    # print('handle', handle, 'addr', addr, 'sender', sender)
    owner = get('asset', 'owner', None, tick)
    # print(owner, addr)
    assert not owner

    put(addr, 'asset', 'owner', addr, tick)
    put(addr, 'asset', 'functions', ['asset_update_ownership', 'asset_update_functions'], tick)

def asset_update_ownership(info, args): # pragma: no cover
    assert args['f'] == 'asset_update_ownership'
    sender = info['sender']
    tick = args['a'][0]
    receiver = args['a'][1]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')
    # print('sender', sender)
    handle = handle_lookup(sender)
    # print('handle', handle)
    addr = handle or sender

    owner = get('asset', 'owner', None, tick)
    # print( owner, addr)
    assert owner == addr
    functions = get('asset', 'functions', None, tick)
    assert type(functions) is list
    assert functions
    put(receiver, 'asset', 'owner', receiver, tick)
    put(receiver, 'asset', 'functions', functions, tick)

def asset_update_functions(info, args): # pragma: no cover
    assert args['f'] == 'asset_update_functions'
    sender = info['sender']
    handle = handle_lookup(sender)
    # print('handle', handle)

    tick = args['a'][0]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

    functions = args['a'][1]
    assert type(functions) is list
    assert functions


def bridge_incoming(info, args): # pragma: no cover
    assert args['f'] == 'bridge_incoming'
    # print('bridge_incoming', args)

    tick = args['a'][0]
    assert type(tick) is str
    assert len(tick) > 0 and len(tick) < 42
    assert tick[0] in string.ascii_uppercase
    assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

    operator = get(tick, 'incoming_operator', None)
    assert operator is not None, "Bridge is not initialized"

    sender = info['sender']
    assert sender == operator, "Only the operator can perform this operation"

    amount = int(args['a'][1])
    assert amount > 0

    receiver = args['a'][2].lower()
    assert len(receiver) <= 42
    assert type(receiver) is str
    if len(receiver) == 42:
        assert receiver.startswith('0x')
        assert set(receiver[2:]) <= set(string.digits+'abcdef')
    else:
        assert len(receiver) > 4

    balance = int(get(tick, 'balance', 0, receiver))
    balance += amount
    put(receiver, tick, 'balance', balance, receiver)

    asset_owner = get('asset', 'owner', None, tick)
    total = int(get(tick, 'total', 0, receiver))
    total += amount
    put(asset_owner, tick, 'total', total)

# def bridge_set_operator(info, args):
#     assert args['f'] == 'bridge_set_operator'
#     print('bridge_set_operator', args)

#     tick = args['a'][0]
#     assert type(tick) is str
#     assert len(tick) > 0 and len(tick) < 42
#     assert tick[0] in string.ascii_uppercase
#     assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

#     asset_owner = get('asset', 'owner', None, tick)
#     sender = info['sender']
#     handle = handle_lookup(sender)
#     addr = handle or sender
#     print('bridge_set_operator', asset_owner, addr)
#     assert addr == asset_owner, "Only the asset owner can perform this operation"

#     operator = args['a'][1].lower()
#     assert type(operator) is str
#     assert len(operator) == 42
#     assert operator.startswith('0x')
#     assert set(operator[2:]) <= set(string.digits+'abcdef')

#     put(addr, tick, 'incoming_operator', operator)

# def bridge_with_token_purchase(info, args):
#     assert args['f'] == 'bridge_with_token_purchase'
#     print('bridge_with_token_purchase', args)

#     tick = args['a'][0]
#     assert type(tick) is str
#     assert len(tick) > 0 and len(tick) < 42
#     assert tick[0] in string.ascii_uppercase
#     assert set(tick) <= set(string.ascii_uppercase+string.digits+'_')

#     operator = get(tick, 'incoming_operator', None)
#     assert operator is not None, "Bridge is not initialized"

#     sender = info['sender']
#     assert sender == operator, "Only the operator can perform this operation"

#     amount = int(args['a'][1])
#     assert amount > 0

#     receiver = args['a'][2].lower()
#     assert len(receiver) <= 42
#     assert type(receiver) is str
#     if len(receiver) == 42:
#         assert receiver.startswith('0x')
#         assert set(receiver[2:]) <= set(string.digits+'abcdef')
#     else:
#         assert len(receiver) > 4

#     balance = int(get(tick, 'balance', 0, receiver))
#     balance += amount
#     put(receiver, tick, 'balance', balance, receiver)

#     asset_owner = get('asset', 'owner', None, tick)
#     total = int(get(tick, 'total', 0, receiver))
#     total += amount
#     put(asset_owner, tick, 'total', total)


# def token_sell_bondingcurve(info, args):
#     assert args['f'] == 'token_sell_bondingcurve'
#     print('token_sell_bondingcurve', args)

#     tick = args['a'][0]

# def token_set_bondingcurve(info, args):
#     assert args['f'] == 'token_set_bondingcurve'
#     tick = args['a'][0]


def trade_limit_order(info, args):
    assert args['f'] == 'trade_limit_order'
    sender = info['sender']
    handle = handle_lookup(sender)
    addr = handle or sender

    base_tick = args['a'][0]
    quote_tick = args['a'][2]
    assert set(base_tick) <= set(string.ascii_uppercase+'_')
    assert set(quote_tick) <= set(string.ascii_uppercase+'_')
    # TODO: make sure quote_tick is set

    pair = '%s_%s' % tuple([base_tick, quote_tick])
    # TODO: check if pair exists

    base_value = int(args['a'][1])
    quote_value = int(args['a'][3])
    assert base_value * quote_value < 0
    K = 10**18

    trade_buy_start = get('trade', f'{pair}_buy_start', 1)
    trade_buy_new = get('trade', f'{pair}_buy_new', 1)
    trade_sell_start = get('trade', f'{pair}_sell_start', 1)
    trade_sell_new = get('trade', f'{pair}_sell_new', 1)

    if base_value < 0 and quote_value > 0:
        balance = get(base_tick, 'balance', 0, addr)
        balance += base_value
        assert balance >= 0
        put(addr, base_tick, 'balance', balance, addr)

        trade_sell_no = trade_sell_start
        while True:
            sell = get('trade', f'{pair}_sell', None, str(trade_sell_no))
            price = - quote_value * K // base_value

            if sell is None:
                put(addr, 'trade', f'{pair}_sell', [addr, base_value, quote_value, price, None, None], str(trade_sell_new))
                trade_sell_new += 1
                put(addr, 'trade', f'{pair}_sell_new', trade_sell_new)
                break

            if price < sell[3]:
                next_sell_id = sell[5]
                put(addr, 'trade', f'{pair}_sell', [addr, base_value, quote_value, price, trade_sell_no, next_sell_id], str(trade_sell_new))
                if next_sell_id is None:
                    trade_sell_start = trade_sell_new
                    put(addr, 'trade', f'{pair}_sell_start', trade_sell_start)
                sell[5] = trade_sell_new
                trade_sell_new += 1
                put(addr, 'trade', f'{pair}_sell_new', trade_sell_new)

                put(addr, 'trade', f'{pair}_sell', sell, str(trade_sell_no))
                if next_sell_id is not None:
                    next_sell = get('trade', f'{pair}_sell', None, str(next_sell_id))
                    if next_sell is not None:
                        next_sell[4] = sell[5]
                        put(addr, 'trade', f'{pair}_sell', next_sell, str(next_sell_id))
                break

            if sell[4] is None:
                put(addr, 'trade', f'{pair}_sell', [addr, base_value, quote_value, price, None, trade_sell_no], str(trade_sell_new))
                put(addr, 'trade', f'{pair}_sell', [sell[0], sell[1], sell[2], sell[3], trade_sell_new, sell[5]], str(trade_sell_no))
                trade_sell_new += 1
                put(addr, 'trade', f'{pair}_sell_new', trade_sell_new)
                break

            trade_sell_no = sell[4]

    elif base_value > 0 and quote_value < 0:
        balance = get(quote_tick, 'balance', 0, addr)
        balance += quote_value
        assert balance >= 0
        put(addr, quote_tick, 'balance', balance, addr)

        trade_buy_no = trade_buy_start
        while True:
            buy = get('trade', f'{pair}_buy', None, str(trade_buy_no))
            price = - quote_value * K // base_value

            if buy is None:
                buy = [addr, base_value, quote_value, price, None, None]
                put(addr, 'trade', f'{pair}_buy', buy, str(trade_buy_new))
                trade_buy_new += 1
                put(addr, 'trade', f'{pair}_buy_new', trade_buy_new)
                break

            if price > buy[3]:
                next_buy_id = buy[5]
                put(addr, 'trade', f'{pair}_buy', [addr, base_value, quote_value, price, trade_buy_no, next_buy_id], str(trade_buy_new))
                if next_buy_id is None:
                    trade_buy_start = trade_buy_new
                    put(addr, 'trade', f'{pair}_buy_start', trade_buy_start)
                buy[5] = trade_buy_new
                trade_buy_new += 1
                put(addr, 'trade', f'{pair}_buy_new', trade_buy_new)

                put(addr, 'trade', f'{pair}_buy', buy, str(trade_buy_no))
                if next_buy_id is not None:
                    next_buy = get('trade', f'{pair}_buy', None, str(next_buy_id))
                    if next_buy is not None:
                        next_buy[4] = buy[5]
                        put(addr, 'trade', f'{pair}_buy', next_buy, str(next_buy_id))
                break

            if buy[4] is None:
                put(addr, 'trade', f'{pair}_buy', [addr, base_value, quote_value, price, None, trade_buy_no], str(trade_buy_new))
                put(addr, 'trade', f'{pair}_buy', [buy[0], buy[1], buy[2], buy[3], trade_buy_new, buy[5]], str(trade_buy_no))
                trade_buy_new += 1
                put(addr, 'trade', f'{pair}_buy_new', trade_buy_new)
                break

            trade_buy_no = buy[4]

    trade_sell_no = trade_sell_start
    highest_buy_price = None

    while True:
        sell = get('trade', f'{pair}_sell', None, str(trade_sell_no))
        if not sell:
            break
        sell_price = sell[3]
        if highest_buy_price and sell_price > highest_buy_price:
            break

        trade_buy_no = trade_buy_start
        while True:
            buy = get('trade', f'{pair}_buy', None, str(trade_buy_no))
            if not buy:
                break
            buy_price = buy[3]
            if highest_buy_price is None:
                highest_buy_price = buy_price
            if sell_price > buy_price:
                trade_buy_no = buy[4]
                continue

            matched_price = sell_price
            dx_base = min(-sell[1], buy[1])
            dx_quote = dx_base * matched_price // K
            sell[1] += dx_base
            sell[2] -= dx_quote
            buy[1] -= dx_base
            buy[2] += dx_quote

            balance = get(base_tick, 'balance', 0, buy[0])
            balance += dx_base
            assert balance >= 0
            put(buy[0], base_tick, 'balance', balance, buy[0])

            balance = get(quote_tick, 'balance', 0, sell[0])
            balance += dx_quote
            assert balance >= 0
            put(sell[0], quote_tick, 'balance', balance, sell[0])

            if buy[1] == 0:
                if buy[4]:
                    prev_buy = get('trade', f'{pair}_buy', None, str(buy[4]))
                    prev_buy[5] = buy[5]
                    put(prev_buy[0], 'trade', f'{pair}_buy', prev_buy, str(buy[4]))

                if buy[5]:
                    next_buy = get('trade', f'{pair}_buy', None, str(buy[5]))
                    next_buy[4] = buy[4]
                    put(next_buy[0], 'trade', f'{pair}_buy', next_buy, str(buy[5]))

                if buy[4] is not None and buy[5] is None:
                    trade_buy_start = buy[4]
                elif buy[4] is None and buy[5] is None:
                    trade_buy_start = trade_buy_new

                if buy[2] < 0:
                    balance = get(quote_tick, 'balance', 0, buy[0])
                    balance -= buy[2]
                    assert balance >= 0
                    put(buy[0], quote_tick, 'balance', balance, buy[0])
    
                put(buy[0], 'trade', f'{pair}_buy', None, str(trade_buy_no))
            else:
                put(buy[0], 'trade', f'{pair}_buy', buy, str(trade_buy_no))

            if sell[1] == 0:
                break
            if buy[4] is None:
                break
            trade_buy_no = buy[4]

        if sell[1] == 0:
            if sell[4]:
                prev_sell = get('trade', f'{pair}_sell', None, str(sell[4]))
                prev_sell[5] = sell[5]
                put(prev_sell[0], 'trade', f'{pair}_sell', prev_sell, str(sell[4]))

            if sell[5]:
                next_sell = get('trade', f'{pair}_sell', None, str(sell[5]))
                next_sell[4] = sell[4]
                put(next_sell[0], 'trade', f'{pair}_sell', next_sell, str(sell[5]))

            if sell[4] is not None and sell[5] is None:
                trade_sell_start = sell[4]
            elif sell[4] is None and sell[5] is None:
                trade_sell_start = trade_sell_new

            if sell[1] < 0:
                balance = get(base_tick, 'balance', 0, sell[0])
                balance -= sell[1]
                assert balance >= 0
                put(sell[0], base_tick, 'balance', balance, sell[0])

            put(sell[0], 'trade', f'{pair}_sell', None, str(trade_sell_no))
        else:
            put(sell[0], 'trade', f'{pair}_sell', sell, str(trade_sell_no))

        if sell[4] is None:
            break
        trade_sell_no = sell[4]

    put('will_change_to_pair_owner', 'trade', f'{pair}_sell_start', trade_sell_start)
    put('will_change_to_pair_owner', 'trade', f'{pair}_buy_start', trade_buy_start)


def trade_market_order(info, args):
    assert args['f'] == 'trade_market_order'
    sender = info['sender']
    handle = handle_lookup(sender)
    addr = handle or sender

    base_tick = args['a'][0]
    quote_tick = args['a'][2]
    assert set(base_tick) <= set(string.ascii_uppercase+'_')
    assert set(quote_tick) <= set(string.ascii_uppercase+'_')
    pair = '%s_%s' % tuple([base_tick, quote_tick])

    base_value = args['a'][1]
    quote_value = args['a'][3]
    trade_sell_start = get('trade', f'{pair}_sell_start', 1)
    trade_buy_start = get('trade', f'{pair}_buy_start', 1)

    K = 10**18
    if quote_value is None and int(base_value) < 0:
        base_value = int(args['a'][1])
        base_balance = get(base_tick, 'balance', 0, addr)
        base_sum = 0

        trade_buy_no = trade_buy_start
        while True:
            buy = get('trade', f'{pair}_buy', None, str(trade_buy_no))
            if buy is None:
                break

            price = buy[3]
            dx_base = min(buy[1], -buy[2] * K // price, -base_value)
            dx_quote = dx_base * price // K
            if dx_base == 0 or dx_quote == 0:
                break
            buy[1] -= dx_base
            buy[2] += dx_quote

            if base_balance - dx_base < 0:
                break
            base_balance -= dx_base
            base_sum += dx_base

            if buy[1] == 0 or buy[1] // price == 0:
                if buy[4]:
                    prev_buy = get('trade', f'{pair}_buy', None, str(buy[4]))
                    prev_buy[5] = buy[5]
                    put(prev_buy[0], 'trade', f'{pair}_buy', prev_buy, str(buy[4]))

                if buy[5]:
                    next_buy = get('trade', f'{pair}_buy', None, str(buy[5]))
                    next_buy[4] = buy[4]
                    put(next_buy[0], 'trade', f'{pair}_buy', next_buy, str(buy[5]))

                if buy[4] is not None and buy[5] is None:
                    trade_buy_start = buy[4]
                    put(addr, 'trade', f'{pair}_buy_start', trade_buy_start)
                elif buy[4] is None and buy[5] is None:
                    trade_buy_new = get('trade', f'{pair}_buy_new', 1)
                    trade_buy_start = trade_buy_new
                    put(addr, 'trade', f'{pair}_buy_start', trade_buy_start)

                if buy[2] < 0:
                    balance = get(quote_tick, 'balance', 0, buy[0])
                    balance -= buy[2]
                    assert balance >= 0
                    put(buy[0], quote_tick, 'balance', balance, buy[0])
    
                put(buy[0], 'trade', f'{pair}_buy', None, str(trade_buy_no))
            else:
                put(buy[0], 'trade', f'{pair}_buy', buy, str(trade_buy_no))

            balance = get(base_tick, 'balance', 0, buy[0])
            balance += dx_base
            assert balance >= 0
            put(addr, base_tick, 'balance', balance, buy[0])

            base_value += dx_base
            assert base_value <= 0
            balance = get(quote_tick, 'balance', 0, addr)
            balance += dx_quote
            assert balance >= 0
            put(addr, quote_tick, 'balance', balance, addr)

            if buy[4] is None:
                break
            trade_buy_no = buy[4]

        balance = get(base_tick, 'balance', 0, addr)
        balance -= base_sum
        assert balance >= 0
        put(addr, base_tick, 'balance', balance, addr)

    elif quote_value is None and int(base_value) > 0:
        base_value = int(args['a'][1])
        quote_balance = get(quote_tick, 'balance', 0, addr)
        quote_sum = 0

        trade_sell_no = trade_sell_start
        while True:
            sell = get('trade', f'{pair}_sell', None, str(trade_sell_no))
            if sell is None:
                break

            price = sell[3]
            dx_base = min(-sell[1], quote_balance * K // price, base_value)
            dx_quote = dx_base * price // K
            if dx_base == 0 or dx_quote == 0:
                break
            sell[1] += dx_base
            sell[2] -= dx_quote

            if quote_balance - dx_quote < 0:
                break
            quote_balance -= dx_quote
            quote_sum += dx_quote

            if sell[1] == 0 or sell[1] // price == 0:
                if sell[4]:
                    prev_sell = get('trade', f'{pair}_sell', None, str(sell[4]))
                    prev_sell[5] = sell[5]
                    put(prev_sell[0], 'trade', f'{pair}_sell', prev_sell, str(sell[4]))

                if sell[5]:
                    next_sell = get('trade', f'{pair}_sell', None, str(sell[5]))
                    next_sell[4] = sell[4]
                    put(next_sell[0], 'trade', f'{pair}_sell', next_sell, str(sell[5]))

                if sell[4] is not None and sell[5] is None:
                    trade_sell_start = sell[4]
                    put(addr, 'trade', f'{pair}_sell_start', trade_sell_start)
                elif sell[4] is None and sell[5] is None:
                    trade_sell_new = get('trade', f'{pair}_sell_new', 1)
                    trade_sell_start = trade_sell_new
                    put(addr, 'trade', f'{pair}_sell_start', trade_sell_start)

                if sell[1] < 0:
                    balance = get(base_tick, 'balance', 0, sell[0])
                    balance -= sell[1]
                    assert balance >= 0
                    put(sell[0], base_tick, 'balance', balance, sell[0])

                put(sell[0], 'trade', f'{pair}_sell', None, str(trade_sell_no))
            else:
                put(sell[0], 'trade', f'{pair}_sell', sell, str(trade_sell_no))

            balance = get(quote_tick, 'balance', 0, sell[0])
            balance += dx_quote
            assert balance >= 0
            put(addr, quote_tick, 'balance', balance, sell[0])

            base_value -= dx_base
            assert base_value >= 0
            balance = get(base_tick, 'balance', 0, addr)
            balance += dx_base
            assert balance >= 0
            put(addr, base_tick, 'balance', balance, addr)

            if sell[4] is None:
                break
            trade_sell_no = sell[4]

        balance = get(quote_tick, 'balance', 0, addr)
        balance -= quote_sum
        assert balance >= 0
        put(addr, quote_tick, 'balance', balance, addr)

    elif base_value is None and int(quote_value) < 0:
        quote_value = int(args['a'][3])
        quote_balance = get(quote_tick, 'balance', 0, addr)
        quote_sum = 0

        trade_sell_no = trade_sell_start
        while True:
            sell = get('trade', f'{pair}_sell', None, str(trade_sell_no))
            if sell is None:
                break

            price = sell[3]
            dx_base = min(-sell[1], -quote_value * K // price)
            dx_quote = dx_base * price // K
            if dx_base == 0 or  dx_quote == 0:
                break
            sell[1] += dx_base
            sell[2] -= dx_quote

            if quote_balance - dx_quote < 0:
                break
            quote_balance -= dx_quote
            quote_sum += dx_quote

            if sell[1] == 0 or sell[1] // price == 0:
                if sell[4]:
                    prev_sell = get('trade', f'{pair}_sell', None, str(sell[4]))
                    prev_sell[5] = sell[5]
                    put(prev_sell[0], 'trade', f'{pair}_sell', prev_sell, str(sell[4]))

                if sell[5]:
                    next_sell = get('trade', f'{pair}_sell', None, str(sell[5]))
                    next_sell[4] = sell[4]
                    put(next_sell[0], 'trade', f'{pair}_sell', next_sell, str(sell[5]))

                if sell[4] is not None and sell[5] is None:
                    trade_sell_start = sell[4]
                    put(addr, 'trade', f'{pair}_sell_start', trade_sell_start)
                elif sell[4] is None and sell[5] is None:
                    trade_sell_new = get('trade', f'{pair}_sell_new', 1)
                    trade_sell_start = trade_sell_new
                    put(addr, 'trade', f'{pair}_sell_start', trade_sell_start)

                if sell[1] < 0:
                    balance = get(base_tick, 'balance', 0, sell[0])
                    balance -= sell[1]
                    assert balance >= 0
                    put(sell[0], base_tick, 'balance', balance, sell[0])

                put(sell[0], 'trade', f'{pair}_sell', None, str(trade_sell_no))
            else:
                put(sell[0], 'trade', f'{pair}_sell', sell, str(trade_sell_no))

            balance = get(quote_tick, 'balance', 0, sell[0])
            balance += dx_quote
            assert balance >= 0
            put(addr, quote_tick, 'balance', balance, sell[0])

            quote_value += dx_quote
            assert quote_value <= 0
            balance = get(base_tick, 'balance', 0, addr)
            balance += dx_base
            assert balance >= 0
            put(addr, base_tick, 'balance', balance, addr)

            if sell[4] is None:
                break
            trade_sell_no = sell[4]

        balance = get(quote_tick, 'balance', 0, addr)
        balance -= quote_sum
        assert balance >= 0
        put(addr, quote_tick, 'balance', balance, addr)

    elif base_value is None and int(quote_value) > 0:
        quote_value = int(args['a'][3])
        base_balance = get(base_tick, 'balance', 0, addr)
        base_sum = 0

        trade_buy_no = trade_buy_start
        while True:
            buy = get('trade', f'{pair}_buy', None, str(trade_buy_no))
            if buy is None:
                break

            price = buy[3]
            dx_base = min(buy[1], base_balance, quote_value * K // price)
            dx_quote = dx_base * price // K
            if dx_base == 0 or dx_quote == 0:
                break
            buy[1] -= dx_base
            buy[2] += dx_quote

            if base_balance - dx_base < 0:
                break
            base_balance -= dx_base
            base_sum += dx_base

            if buy[1] == 0 or buy[1] // price == 0:
                if buy[4]:
                    prev_buy = get('trade', f'{pair}_buy', None, str(buy[4]))
                    prev_buy[5] = buy[5]
                    put(prev_buy[0], 'trade', f'{pair}_buy', prev_buy, str(buy[4]))

                if buy[5]:
                    next_buy = get('trade', f'{pair}_buy', None, str(buy[5]))
                    next_buy[4] = buy[4]
                    put(next_buy[0], 'trade', f'{pair}_buy', next_buy, str(buy[5]))

                if buy[4] is not None and buy[5] is None:
                    trade_buy_start = buy[4]
                    put(addr, 'trade', f'{pair}_buy_start', trade_buy_start)
                elif buy[4] is None and buy[5] is None:
                    trade_buy_new = get('trade', f'{pair}_buy_new', 1)
                    trade_buy_start = trade_buy_new
                    put(addr, 'trade', f'{pair}_buy_start', trade_buy_start)

                if buy[2] < 0:
                    balance = get(quote_tick, 'balance', 0, buy[0])
                    balance -= buy[2]
                    assert balance >= 0
                    put(buy[0], quote_tick, 'balance', balance, buy[0])
    
                put(buy[0], 'trade', f'{pair}_buy', None, str(trade_buy_no))
            else:
                put(buy[0], 'trade', f'{pair}_buy', buy, str(trade_buy_no))

            balance = get(base_tick, 'balance', 0, buy[0])
            balance += dx_base
            assert balance >= 0
            put(addr, base_tick, 'balance', balance, buy[0])

            quote_value -= dx_quote
            assert quote_value >= 0
            balance = get(quote_tick, 'balance', 0, addr)
            balance += dx_quote
            assert balance >= 0
            put(addr, quote_tick, 'balance', balance, addr)

            if buy[4] is None:
                break
            trade_buy_no = buy[4]

        balance = get(base_tick, 'balance', 0, addr)
        balance -= base_sum
        assert balance >= 0
        put(addr, base_tick, 'balance', balance, addr)
