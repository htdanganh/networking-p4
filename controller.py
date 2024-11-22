from p4utils.utils.helper import load_topo
from p4utils.utils.sswitch_p4runtime_API import SimpleSwitchP4RuntimeAPI # Not needed anymore
from p4utils.utils.sswitch_thrift_API import SimpleSwitchThriftAPI

import time

topo = load_topo('topology.json')
controllers = {}

# Note: we now use the SimpleSwitchThriftAPI to communicate with the switches
# and not the P4RuntimeAPI anymore.
for p4switch in topo.get_p4switches():
    thrift_port = topo.get_thrift_port(p4switch)
    controllers[p4switch] = SimpleSwitchThriftAPI(thrift_port)

# The following lines enable the forwarding as required for assignment 0.
controllers['s1'].table_add('repeater', 'forward', ['1'], ['2'])
controllers['s1'].table_add('repeater', 'forward', ['3'], ['1'])

controllers['s2'].table_add('repeater', 'forward', ['1'], ['2'])
controllers['s2'].table_add('repeater', 'forward', ['2'], ['1'])

controllers['s4'].table_add('repeater', 'forward', ['1'], ['2'])
controllers['s4'].table_add('repeater', 'forward', ['2'], ['1'])

controllers['s3'].table_add('repeater', 'forward', ['1'], ['2'])
controllers['s3'].table_add('repeater', 'forward', ['2'], ['3'])

def safe_register_read(controller, register_name, index):
    """Safely read a register value with error handling."""
    try:
        value = controller.register_read(register_name, index)
        return int(value) if value is not None else 0
    except Exception as e:
        print(f"Error reading register {register_name}[{index}]: {e}")
        return 0

def get_port_stats(s1, s2, counter_idx):
    """Get port statistics for a link between two switches."""
    try:
        s1_port = topo.node_to_node_port_num(s1, s2)
        s2_port = topo.node_to_node_port_num(s2, s1)
        
        if counter_idx == 0:
            s1_egress = safe_register_read(controllers[s1], 'egress_counters_0', s1_port)
            s2_ingress = safe_register_read(controllers[s2], 'ingress_counters_0', s2_port)
        else:
            s1_egress = safe_register_read(controllers[s1], 'egress_counters_1', s1_port)
            s2_ingress = safe_register_read(controllers[s2], 'ingress_counters_1', s2_port)
            
        return s1_port, s2_port, s1_egress, s2_ingress
    except Exception as e:
        print(f"Error getting port stats for {s1}->{s2}: {e}")
        return None, None, 0, 0

def check_failure(s1, s2, counter_idx):
    """Check for failures between two switches."""
    s1_port, s2_port, s1_egress, s2_ingress = get_port_stats(s1, s2, counter_idx)
    
    if s1_port is None:
        return False
        
    if s1_egress > 0: 
        if s1_egress != s2_ingress:
            loss = s1_egress - s2_ingress
            loss_percentage = (loss / float(s1_egress) * 100)
            
            if loss_percentage > 1:
                print(f"\nALERT: Packet loss detected on link {s1}->{s2}")
                print(f"Packets sent from {s1} port {s1_port}: {s1_egress}")
                print(f"Packets received at {s2} port {s2_port}: {s2_ingress}")
                print(f"Loss: {loss} packets ({loss_percentage:.1f}%)")
                return True
    return False

def print_link_stats(s1, s2, counter_idx):
    s1_port, s2_port, s1_egress, s2_ingress = get_port_stats(s1, s2, counter_idx)
    if s1_port is not None:
        print(f"\nLink {s1}->{s2} (counter {counter_idx}):")
        print(f"  {s1} port {s1_port} egress: {s1_egress}")
        print(f"  {s2} port {s2_port} ingress: {s2_ingress}")

def reset_counters(switch, port, counter_idx):
    try:
        controllers[switch].register_write(f'egress_counters_{counter_idx}', port, 0)
        controllers[switch].register_write(f'ingress_counters_{counter_idx}', port, 0)
    except Exception as e:
        print(f"Error resetting counters for {switch} port {port}: {e}")

current_counter = 0
for switch in topo.get_p4switches():
    controllers[switch].register_write('active_counter_register', 0, current_counter)

while True:
    try:
        time.sleep(1)
        
        inactive_counter = 1 - current_counter
        
        links = [
            ('s1', 's2'), ('s2', 's3'), ('s3', 's4'),
            ('s2', 's1'), ('s3', 's2'), ('s4', 's3')  
        ]
        
        for s1, s2 in links:
            check_failure(s1, s2, inactive_counter)
            print_link_stats(s1, s2, inactive_counter)
        
        current_counter = 1 - current_counter
        for switch in topo.get_p4switches():
            controllers[switch].register_write('active_counter_register', 0, current_counter)
        
        for switch in topo.get_p4switches():
            neighbors = topo.get_neighbors(switch)
            for neighbor in neighbors:
                port = topo.node_to_node_port_num(switch, neighbor)
                reset_counters(switch, port, inactive_counter)
                
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(1)