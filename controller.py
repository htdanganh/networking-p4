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

def check_counters():
    for switch in topo.get_p4switches():
        neighbors = topo.get_neighbors(switch)
        for neighbor in neighbors:
            if neighbor in topo.get_p4switches():  # Ensure the neighbor is a switch
                port_out = topo.node_to_node_port_num(switch, neighbor)
                port_in = topo.node_to_node_port_num(neighbor, switch)

                try:
                    # Read inactive counters
                    egress_counter = controllers[switch].register_read("egress_counter_inactive", index=port_out)
                    ingress_counter = controllers[neighbor].register_read("ingress_counter_inactive", index=port_in)

                    # Compare counters to detect failure
                    if egress_counter != ingress_counter:
                        print(f"Packet loss detected: {switch} (port {port_out}) -> {neighbor} (port {port_in})")
                    else:
                        print(f"No packet loss: {switch} (port {port_out}) -> {neighbor} (port {port_in})")
                except Exception as e:
                    print(f"Error reading counters for link {switch} -> {neighbor}: {e}")


def switch_counters():
    for switch in controllers:
        try:
            controllers[switch].register_write("counter_index", index=0, value=1)
            print(f"Switched counters on {switch}")
        except Exception as e:
            print(f"Error switching counters on {switch}: {e}")


def print_link(node1, node2):
    port1 = topo.node_to_node_port_num(node1, node2)
    port2 = topo.node_to_node_port_num(node2, node1)

    egress_active = controllers[node1].register_read("egress_counter_active", index=port1)
    ingress_active = controllers[node2].register_read("ingress_counter_active", index=port2)
    egress_inactive = controllers[node1].register_read("egress_counter_inactive", index=port1)
    ingress_inactive = controllers[node2].register_read("ingress_counter_inactive", index=port2)

    print(f"{node1} -> {node2}:")
    print(f"  Egress Active: {egress_active}, Egress Inactive: {egress_inactive}")
    print(f"  Ingress Active: {ingress_active}, Ingress Inactive: {ingress_inactive}")

while True:
    check_counters()

    switch_counters()

    time.sleep(1)