

def make_src_id(device_id, obj_id):
    return f'{obj_id}@{device_id}'

def make_obj_id(obj_type, obj_instance):
    return f'{obj_type}:{obj_instance}'

def parse_obj_id(obj_srcid):
    obj_type, obj_instance = obj_srcid.split(':')
    return {
        'obj_type': obj_type,
        'obj_instance': obj_instance
    }

def striding_window(l, w_size):
    curr_idx = 0
    while curr_idx < len(l):
        yield l[curr_idx:curr_idx + w_size]
        curr_idx += w_size
