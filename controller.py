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
    try:
        value = controller.register_read(register_name, index)
        return int(value) if value is not None else 0
    except Exception as e:
        print(f"Error reading register {register_name}[{index}]: {e}")
        return 0

def print_link_stats(s1, s2):
    try:
        s1_port = topo.node_to_node_port_num(s1, s2)
        s2_port = topo.node_to_node_port_num(s2, s1)
        
        # Read both counter sets
        s1_egress_0 = safe_register_read(controllers[s1], 'egress_counters_0', s1_port - 1)
        s1_egress_1 = safe_register_read(controllers[s1], 'egress_counters_1', s1_port - 1)
        s2_ingress_0 = safe_register_read(controllers[s2], 'ingress_counters_0', s2_port - 1)
        s2_ingress_1 = safe_register_read(controllers[s2], 'ingress_counters_1', s2_port - 1)
        
        print(f"\nLink {s1}->{s2}:")
        print(f"  {s1} port {s1_port} egress counter 0: {s1_egress_0}")
        print(f"  {s2} port {s2_port} ingress counter 0: {s2_ingress_0}")
        print(f"  {s1} port {s1_port} egress counter 1: {s1_egress_1}")
        print(f"  {s2} port {s2_port} ingress counter 1: {s2_ingress_1}")
    except Exception as e:
        print(f"Error printing link stats for {s1}->{s2}: {e}")

def check_failure(s1, s2, counter_idx):
    try:
        s1_port = topo.node_to_node_port_num(s1, s2)
        s2_port = topo.node_to_node_port_num(s2, s1)
        
        # Read the values from both switches
        s1_egress = safe_register_read(controllers[s1], 
                                     f'egress_counters_{counter_idx}', 
                                     s1_port - 1)
        s2_ingress = safe_register_read(controllers[s2], 
                                      f'ingress_counters_{counter_idx}', 
                                      s2_port - 1)
        
        # Only check for packet loss if we've seen some traffic
        if s1_egress > 0 and s1_egress != s2_ingress:
            loss = s1_egress - s2_ingress
            loss_percentage = (loss / s1_egress * 100)
            if loss_percentage >= 1.0:  # Only alert if loss is >= 1%
                print(f"\nALERT: Packet loss detected on link {s1}->{s2}")
                print(f"Packets sent from {s1} port {s1_port}: {s1_egress}")
                print(f"Packets received at {s2} port {s2_port}: {s2_ingress}")
                print(f"Loss: {loss} packets ({loss_percentage:.1f}%)")
                return True
    except Exception as e:
        print(f"Error checking failure for {s1}->{s2}: {e}")
    return False

def reset_inactive_counters(switch, counter_idx):
    try:
        port_count = 3  # Maximum number of ports
        for port in range(port_count):
            controllers[switch].register_write(f'egress_counters_{counter_idx}', port, 0)
            controllers[switch].register_write(f'ingress_counters_{counter_idx}', port, 0)
    except Exception as e:
        print(f"Error resetting counters for switch {switch}: {e}")

current_counter = 0
for switch in topo.get_p4switches():
    controllers[switch].register_write('active_counter_register', 0, current_counter)

while True:
    try:
        time.sleep(1)
        
        # Store the current inactive counter
        inactive_counter = 1 - current_counter
        
        # Check all switch-to-switch links in both directions
        switch_links = [
            ('s1', 's2'),  # Top path
            ('s2', 's3'),
            ('s1', 's4'),  # Bottom path
            ('s4', 's3')
        ]
        
        # Check for failures using the inactive counter
        for s1, s2 in switch_links:
            check_failure(s1, s2, inactive_counter)
            check_failure(s2, s1, inactive_counter)
            print_link_stats(s1, s2)
            print_link_stats(s2, s1)
        
        # Switch active counters
        current_counter = 1 - current_counter
        for switch in topo.get_p4switches():
            controllers[switch].register_write('active_counter_register', 0, current_counter)
        
        # Give a small delay for counter switching to propagate
        time.sleep(0.1)
        
    except Exception as e:
        print(f"Error in main loop: {e}")
        time.sleep(1)