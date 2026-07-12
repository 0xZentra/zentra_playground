def handle_reg(info, args):
    assert args['f'] == 'handle_reg'
    sender = info['sender']
    addr = handle_lookup(sender)
    handle = args['a'][0]
    assert type(handle) is str
    assert len(handle) > 4 and len(handle) < 42
    assert handle[0] in string.ascii_lowercase
    assert set(handle) <= set(string.digits + string.ascii_lowercase + '_')

    existing, _ = get('handle', 'handle2addr', None, handle)
    assert existing is None, "Handle already exists"

    bound_handle, _ = get('handle', 'addr2handle', None, addr)
    assert bound_handle is None, "Address already has a handle"

    put(addr, 'handle', 'handle2addr', addr, handle)
    put(addr, 'handle', 'addr2handle', handle, addr)

    event('HandleRegistered', [handle, addr])


def handle_update(info, args):
    assert args['f'] == 'handle_update'
    sender = info['sender']
    old_addr = handle_lookup(sender)
    handle = args['a'][0]
    assert type(handle) is str
    assert len(handle) > 4 and len(handle) < 42
    assert handle[0] in string.ascii_lowercase
    assert set(handle) <= set(string.digits + string.ascii_lowercase + '_')

    owner, _ = get('handle', 'handle2addr', None, handle)
    assert owner is not None, "Handle not found"
    assert owner == old_addr, "Not the handle owner"

    new_addr = args['a'][1].lower()
    assert len(new_addr) <= 42
    assert type(new_addr) is str
    if len(new_addr) == 42:
        assert new_addr.startswith('0x')
        assert set(new_addr[2:]) <= set(string.digits + 'abcdef')
    else:
        assert len(new_addr) > 4

    new_bound_handle, _ = get('handle', 'addr2handle', None, new_addr)
    assert new_bound_handle is None, "New address already has a handle"

    put(new_addr, 'handle', 'handle2addr', new_addr, handle)
    put(old_addr, 'handle', 'addr2handle', None, old_addr)
    put(new_addr, 'handle', 'addr2handle', handle, new_addr)

    event('HandleUpdated', [handle, old_addr, new_addr])
