/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

//My includes
#include "include/metadata.p4"
#include "include/headers.p4"
#include "include/parsers.p4"

/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    register<bit<32>>(2) ingress_counter_active; 
    register<bit<32>>(2) ingress_counter_inactive;

    action increment_ingress_counter() {

        bit<32> counter_value;
        ingress_counter_active.read(counter_value, standard_metadata.ingress_port);
        
        counter_value = counter_value + 1;
        ingress_counter_active.write(standard_metadata.ingress_port, counter_value);
        
        meta.ingress_counter_value = counter_value;
    }

    action forward(bit<9> egress_port) {
        standard_metadata.egress_spec = egress_port;
    }

    table repeater {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            forward;
            NoAction;
        }
        size = 2;
        default_action = NoAction;
    }

    apply {
        // Increment the active counter
        increment_ingress_counter();

        // Apply the repeater logic
        repeater.apply();
    }
}


/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    register<bit<32>>(2) egress_counter_active; 
    register<bit<32>>(2) egress_counter_inactive;

    action increment_egress_counter() {
        bit<32> counter_value;
        egress_counter_active.read(counter_value, standard_metadata.egress_port);
        
        counter_value = counter_value + 1;
        egress_counter_active.write(standard_metadata.egress_port, counter_value);
        
        meta.egress_counter_value = counter_value;
    }

    action set_ecn() {
        hdr.ipv4.ecn = meta.counter_index;
    }

    apply {
        increment_egress_counter();

        if (hdr.ipv4.isValid()) {
            set_ecn();
        }
    }
}


/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
    apply { 

    }
}


/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;