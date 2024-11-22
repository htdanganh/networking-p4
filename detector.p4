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

    register<bit<32>>(2) ingress_counters_0;
    register<bit<32>>(2) ingress_counters_1;
    register<bit<1>>(1) active_counter_register;

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
        active_counter_register.read(meta.active_counter, 0);
        
        meta.ingress_port = standard_metadata.ingress_port;
        
        if (hdr.ipv4.isValid()) {
            if (hdr.ipv4.ecn == 0) {
                ingress_counters_0.read(meta.counter_value, (bit<32>)standard_metadata.ingress_port);
                meta.counter_value = meta.counter_value + 1;
                ingress_counters_0.write((bit<32>)standard_metadata.ingress_port, meta.counter_value);
            } else {
                ingress_counters_1.read(meta.counter_value, (bit<32>)standard_metadata.ingress_port);
                meta.counter_value = meta.counter_value + 1;
                ingress_counters_1.write((bit<32>)standard_metadata.ingress_port, meta.counter_value);
            }
        }

        repeater.apply();
    }
}


/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    register<bit<32>>(2) egress_counters_0;
    register<bit<32>>(2) egress_counters_1;
    
    apply {
        if (hdr.ipv4.isValid()) {
            // Read active counter value
            if (meta.active_counter == 0) {

                egress_counters_0.read(meta.counter_value, (bit<32>)standard_metadata.egress_port);
                meta.counter_value = meta.counter_value + 1;
                egress_counters_0.write((bit<32>)standard_metadata.egress_port, meta.counter_value);

                hdr.ipv4.ecn = 0;
            } else {

                egress_counters_1.read(meta.counter_value, (bit<32>)standard_metadata.egress_port);
                meta.counter_value = meta.counter_value + 1;
                egress_counters_1.write((bit<32>)standard_metadata.egress_port, meta.counter_value);

                hdr.ipv4.ecn = 1;
            }
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