

import code
import rlcompleter
import sys
import threading
try:
    import readline
except:
    pass

import json
import tornado.web
import tornado.ioloop

try:
    from eth_utils import keccak
except ImportError:
    keccak = None

import space
import rpc
import func


func.load_all_zips()

GLOBAL_FUNCTIONS = func.namespace


class GetLatestStateAPIHandler(tornado.web.RequestHandler):
    def get(self):
        from urllib.parse import unquote
        prefix = unquote(self.get_argument('prefix'))
        print('get_latest_state:', prefix)
        
        # format: asset-var:key (e.g., BTC-balance:0xabc...)
        if '-' not in prefix:
            self.finish({'result': None})
            return
        
        idx = prefix.index('-')
        asset = prefix[:idx]
        rest = prefix[idx+1:]
        
        if ':' in rest:
            var, key = rest.split(':', 1)
        else:
            var = rest
            key = None
        
        value, owner = space.get(asset, var, None, key)
        print('value:', value, 'owner:', owner)
        self.finish({'result': value, 'owner': owner})

class QueryRecentStateAPIHandler(tornado.web.RequestHandler):
    def get(self):
        prefix = self.get_argument('prefix')
        print(prefix)


class OrderbookAPIHandler(tornado.web.RequestHandler):
    def get(self):
        base = self.get_argument('base')
        quote = self.get_argument('quote')
        pair = f'{base}_{quote}'
        
        buys = []
        sells = []
        
        buy_start, _ = space.get('trade', f'{pair}_buy_start', 1)
        sell_start, _ = space.get('trade', f'{pair}_sell_start', 1)
        
        buy_id = buy_start
        while buy_id:
            buy, _ = space.get('trade', f'{pair}_buy', None, str(buy_id))
            if buy:
                buys.append({
                    'id': buy_id,
                    'owner': buy[0],
                    'base': str(buy[1]),
                    'quote': str(buy[2]),
                    'price': str(buy[3]),
                    'next': buy[4]
                })
                buy_id = buy[4]
            else:
                break
        
        sell_id = sell_start
        while sell_id:
            sell, _ = space.get('trade', f'{pair}_sell', None, str(sell_id))
            if sell:
                sells.append({
                    'id': sell_id,
                    'owner': sell[0],
                    'base': str(sell[1]),
                    'quote': str(sell[2]),
                    'price': str(sell[3]),
                    'next': sell[4]
                })
                sell_id = sell[4]
            else:
                break
        
        self.finish({'buys': buys, 'sells': sells, 'pair': pair})


class HistoryAPIHandler(tornado.web.RequestHandler):
    def get(self):
        base = self.get_argument('base')
        quote = self.get_argument('quote')
        pair = f'{base}_{quote}'

        start_block = int(self.get_argument('start_block', 0))
        end_block = int(self.get_argument('end_block', space.latest_block_number))

        candle_map = {}
        for block_num in range(start_block, end_block + 1):
            block_events = space.events.get(block_num, [])
            for evt in block_events:
                if evt['event'] in ('TradeLimitTake', 'TradeMarketTake') and pair in evt['args']:
                    price = int(evt['args'][4])
                    if price == 0:
                        continue
                    base_amount = int(evt['args'][3])
                    usdc_amount = base_amount * price // (10 ** 6)

                    if block_num not in candle_map:
                        candle_map[block_num] = {
                            'time': block_num,
                            'block': block_num,
                            'open': 0,
                            'high': 0,
                            'low': 0,
                            'close': 0,
                            'volume': 0,
                        }
                    c = candle_map[block_num]
                    if c['open'] == 0:
                        c['open'] = price
                        c['high'] = price
                        c['low'] = price
                    c['close'] = price
                    c['high'] = max(c['high'], price)
                    c['low'] = min(c['low'], price)
                    c['volume'] += usdc_amount

        candles = list(candle_map.values())
        for i, c in enumerate(candles):
            c['open'] = c['open'] / (10 ** 6)
            c['high'] = c['high'] / (10 ** 6)
            c['low'] = c['low'] / (10 ** 6)
            c['close'] = c['close'] / (10 ** 6)

        candles.sort(key=lambda x: x['time'])

        self.finish({
            'candles': candles,
            'pair': pair,
            'start_block': start_block,
            'end_block': end_block,
            'latest_block': space.latest_block_number
        })


class EventsAPIHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

        chain = self.get_argument('chain', 'base')

        block_number = self.get_argument('blockno', None)
        if block_number is not None:
            block_number = int(block_number)
            block_hash = space.block_hashes.get(block_number, '')
            tx_hashes = space.blocks.get(block_number, [])

            block_events = space.events.get(block_number, [])

            events_with_tx = []
            for i, evt in enumerate(block_events):
                evt_with_tx = dict(evt)
                evt_with_tx['tx_index'] = i
                evt_with_tx['tx_hash'] = tx_hashes[i] if i < len(tx_hashes) else ''
                events_with_tx.append(evt_with_tx)

            self.finish({
                'tx_hashes': tx_hashes,
                'events': events_with_tx,
                'blockno': block_number,
                'block_hash': block_hash,
                'chain': chain
            })
            return

        tx_hash = self.get_argument('txhash', '')
        tx_hash = tx_hash.replace('0x', '')

        if tx_hash in space.transactions:
            tx = space.transactions[tx_hash]
            block_number = tx.get('blockNumber', 0)
            block_events = space.events.get(block_number, [])

            events_with_tx = []
            for i, evt in enumerate(block_events):
                evt_with_tx = dict(evt)
                evt_with_tx['tx_index'] = i
                evt_with_tx['tx_hash'] = tx_hash
                events_with_tx.append(evt_with_tx)

            self.finish({'tx_hash': tx_hash, 'blockno': block_number, 'events': events_with_tx, 'chain': chain})
        else:
            self.finish({'tx_hash': tx_hash, 'events': [], 'chain': chain})


# === Debug Pages ===

class DebugBaseHandler(tornado.web.RequestHandler):
    def render_debug_page(self, template_name, **kwargs):
        self.render(f"debug/{template_name}", **kwargs)


class DebugOverviewHandler(DebugBaseHandler):
    def get(self):
        total_state_entries = sum(len(s) for s in space.states.values())
        total_events = sum(len(v) for v in space.events.values())
        total_txs = len(space.transactions)

        self.render_debug_page("overview.html",
            title="Overview",
            latest_block=space.latest_block_number,
            total_blocks=len(space.blocks),
            total_txs=total_txs,
            total_events=total_events,
            total_state_entries=total_state_entries
        )


class DebugBlocksHandler(DebugBaseHandler):
    def get(self):
        blocks = []
        for blk_num in sorted(space.blocks.keys(), reverse=True)[:100]:
            blk_hash = space.block_hashes.get(blk_num, None)
            tx_count = len(space.blocks.get(blk_num, []))
            evt_count = len(space.events.get(blk_num, []))
            hash_str = (str(blk_hash)[:16] + "...") if blk_hash else "None"
            blocks.append({
                "num": blk_num,
                "hash": hash_str,
                "time": "N/A",
                "tx_count": tx_count,
                "evt_count": evt_count
            })
        self.render_debug_page("blocks.html", title="Blocks", blocks=blocks)


class DebugBlockHandler(DebugBaseHandler):
    def get(self, block_num):
        blk_num = int(block_num)
        blk_hash = space.block_hashes.get(blk_num, None)
        txs = space.blocks.get(blk_num, [])
        evts = space.events.get(blk_num, [])

        tx_list = []
        for tx in txs:
            tx_hash = tx[1] if isinstance(tx, tuple) else tx
            tx_data = space.transactions.get(tx_hash, {})
            tx_list.append({"hash": str(tx_hash), "data": json.dumps(tx_data, indent=2)})

        evt_list = []
        for evt in evts:
            evt_list.append({"event": str(evt.get("event")), "args": json.dumps(evt.get("args"), indent=2)})

        hash_str = str(blk_hash) if blk_hash else "None"

        self.render_debug_page("block.html",
            title="Block " + str(blk_num),
            blk_num=blk_num,
            blk_hash=hash_str,
            blk_time="N/A",
            txs=tx_list,
            evts=evt_list
        )


class DebugEventsHandler(DebugBaseHandler):
    def get(self):
        blocks = []
        for blk_num in sorted(space.events.keys(), reverse=True):
            evts = space.events[blk_num]
            evt_list = []
            for evt in evts:
                evt_list.append({"event": str(evt.get("event")), "args": json.dumps(evt.get("args"), indent=2)})
            blocks.append({"num": blk_num, "count": len(evts), "events": evt_list})
        self.render_debug_page("events.html", title="Events", blocks=blocks)


class DebugStateHandler(DebugBaseHandler):
    def get(self):
        prefix = self.get_argument("prefix", "")
        entries = []
        count = 0
        max_entries = 500
        for block_num in sorted(space.states.keys(), reverse=True):
            state = space.states[block_num]
            for key in sorted(state.keys()):
                if prefix and not key.startswith(prefix):
                    continue
                addr, value = state[key]
                entries.append({"key": str(key), "owner": str(addr), "value": str(value), "block_num": block_num})
                count += 1
                if count >= max_entries:
                    break
            if count >= max_entries:
                break
        self.render_debug_page("state.html",
            title="State Browser",
            prefix=prefix,
            entries=entries,
            count=count,
            max_entries=max_entries
        )


class DebugTransactionsHandler(DebugBaseHandler):
    def get(self):
        transactions = []
        for tx_hash, tx_data in sorted(space.transactions.items()):
            transactions.append({"hash": str(tx_hash), "data": json.dumps(tx_data, indent=2)})
        self.render_debug_page("transactions.html", title="Transactions", transactions=transactions)


# class EventsAPIHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.set_header("Access-Control-Allow-Origin", "*")
#         self.set_header("Access-Control-Allow-Headers", "x-requested-with")
#         self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

#         global global_input
#         chain = self.get_argument('chain', 'base')
#         assert chain in setting.chains
#         it1 = global_input.iteritems()
#         events = []
#         try:
#             block_number = int(self.get_argument('blockno', None))
#         except:
#             tx_hash = self.get_argument('txhash', '')
#             tx_hash = tx_hash.replace('0x', '')
#             k = ('%s-tx-%s-' % (chain, tx_hash) ).encode('utf8')
#             it1.seek(k)
#             for key1, value_json1 in it1:
#                 print('key1', key1)
#                 if not key1.startswith(k):
#                     break
#                 tx = json.loads(value_json1)
#                 events.append([tx_hash, tx['events']])

#             self.finish({'events': events, 'tx_hash': tx_hash, 'chain':chain})
#             return

#         it = global_input.iteritems()
#         reversed_height = str(setting.REVERSED_NO - block_number).zfill(16)
#         k = ('%s-block-%s-' % (chain, reversed_height)).encode('utf8')
#         it.seek(k)

#         for key, value_json in it:
#             # print('block', block_number, key)
#             if not key.startswith(k):
#                 break

#             _, _, _, block_hash = key.decode('utf8').split('-')
#             block = json.loads(value_json)
#             tx_hashes = block.get('transactions', [])
#             # chain = block['chain']
#             for tx_hash in tx_hashes:
#                 k = ('%s-tx-%s-' % (chain, tx_hash) ).encode('utf8')
#                 it1.seek(k)
#                 for key1, value_json1 in it1:
#                     print('key1', key1)
#                     if not key1.startswith(k):
#                         break
#                     tx = json.loads(value_json1)
#                     events.append([tx_hash, tx['events']])
#                     break

#             break
#         self.finish({'events': events, 'blockno': block_number, 'block_hash': block_hash, 'chain':chain})


def start_server():
    space._init_block_mode()
    app = tornado.web.Application([
        # (r'/(favicon\.ico)', tornado.web.StaticFileHandler, {'path': 'static/'}),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
        # (r"/state", StateHandler),
        (r'/debug/', DebugOverviewHandler),
        (r'/debug/blocks', DebugBlocksHandler),
        (r'/debug/block/(\d+)', DebugBlockHandler),
        (r'/debug/events', DebugEventsHandler),
        (r'/debug/state', DebugStateHandler),
        (r'/debug/transactions', DebugTransactionsHandler),
        (r"/", rpc.RPCHandler),
        (r'/api/get_latest_state', GetLatestStateAPIHandler),
        (r'/api/query_recent_state', QueryRecentStateAPIHandler),
        (r'/api/orderbook', OrderbookAPIHandler),
        (r'/api/history', HistoryAPIHandler),
        (r'/api/events', EventsAPIHandler),
    ], template_path="templates")
    app.listen(8545)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True  # Thread will close when main program exits
    server_thread.start()
    try:
        readline.parse_and_bind("tab: complete")
    except:
        pass

    print("Server started at http://127.0.0.1:8545")
    print("Debug page: http://127.0.0.1:8545/debug/")
    print()

    code.interact(banner="""
    Zentra Interactive python console
    Available commands:
    - put(owner, asset, var, value, key=None)  # Store state
    - get(asset, var, default=None, key=None)  # Access state
    - blocknumber()  # Current block number
    - nextblock()  # Start next block
    - setsender()  # Set sender
    - states  # View all states
    - sender  # Current sender

    Example:
    >>> put('alice', 'USDC', 'balance', 100, 'alice')
    >>> get('USDC', 'balance', 0, 'alice')
    100
    >>> states
    {0: {'asset-balance': ('alice', 100)}}
    >>> nextblock()
    >>> setsender(a[0])
    >>> asset_create('USDC')
    Ok, let's start!
    """, local=func.namespace)

