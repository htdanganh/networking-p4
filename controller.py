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

def print_link(s1, s2):
    s1_port = topo.node_to_node_port_num(s1, s2)
    s2_port = topo.node_to_node_port_num(s2, s1)
    
    # Get counter values
    s1_egress_0 = controllers[s1].register_read('egress_counters_0', s1_port)
    s1_egress_1 = controllers[s1].register_read('egress_counters_1', s1_port)
    s2_ingress_0 = controllers[s2].register_read('ingress_counters_0', s2_port)
    s2_ingress_1 = controllers[s2].register_read('ingress_counters_1', s2_port)
    
    print(f"\nLink {s1}->{s2}:")
    print(f"  {s1} egress counter 0: {s1_egress_0}")
    print(f"  {s2} ingress counter 0: {s2_ingress_0}")
    print(f"  {s1} egress counter 1: {s1_egress_1}")
    print(f"  {s2} ingress counter 1: {s2_ingress_1}")

def check_failure(s1, s2, counter_idx):
    s1_port = topo.node_to_node_port_num(s1, s2)
    s2_port = topo.node_to_node_port_num(s2, s1)
    
    if counter_idx == 0:
        s1_egress = controllers[s1].register_read('egress_counters_0', s1_port)
        s2_ingress = controllers[s2].register_read('ingress_counters_0', s2_port)
    else:
        s1_egress = controllers[s1].register_read('egress_counters_1', s1_port)
        s2_ingress = controllers[s2].register_read('ingress_counters_1', s2_port)
    
    if s1_egress != s2_ingress:
        loss = s1_egress - s2_ingress
        loss_percentage = (loss / s1_egress * 100) if s1_egress > 0 else 0
        print(f"\nALERT: Packet loss detected on link {s1}->{s2}")
        print(f"Packets sent: {s1_egress}, Packets received: {s2_ingress}")
        print(f"Loss: {loss} packets ({loss_percentage:.1f}%)")
        return True
    return False

# Initialize active counter to 0
current_counter = 0
for switch in topo.get_p4switches():
    controllers[switch].register_write('active_counter_register', 0, 0)

while True:
    time.sleep(1)
    
    inactive_counter = 1 - current_counter
    
    links = [('s1', 's2'), ('s2', 's3'), ('s3', 's4')]
    for s1, s2 in links:
        check_failure(s1, s2, inactive_counter)
        check_failure(s2, s1, inactive_counter)
        print_link(s1, s2)
    
    current_counter = 1 - current_counter
    for switch in topo.get_p4switches():
        controllers[switch].register_write('active_counter_register', 0, current_counter)
    
    inactive_counter = 1 - current_counter
    for switch in topo.get_p4switches():
        for port in range(2):
            if inactive_counter == 0:
                controllers[switch].register_write('egress_counters_0', port, 0)
                controllers[switch].register_write('ingress_counters_0', port, 0)
            else:
                controllers[switch].register_write('egress_counters_1', port, 0)
                controllers[switch].register_write('ingress_counters_1', port, 0)
