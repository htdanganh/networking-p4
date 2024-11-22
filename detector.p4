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

    // Register arrays for ingress packet counting
    register<bit<32>>(2) ingress_counters_0;
    register<bit<32>>(2) ingress_counters_1;
    
    // Register to track which counter set is active (still 1 bit in register)
    register<bit<1>>(1) active_counter_register;

    action forward(bit<9> egress_port){
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
        // Read which counter is currently active
        bit<1> active_counter;
        active_counter_register.read(active_counter, 0);
        
        // Cast to 2 bits for metadata
        meta.active_counter = (bit<2>)active_counter;
        
        // Calculate port index (0-based)
        meta.ingress_port_index = (bit<32>)(standard_metadata.ingress_port - 1);
        
        // Increment the appropriate counter based on active counter
        if (active_counter == 0) {
            bit<32> count;
            ingress_counters_0.read(count, meta.ingress_port_index);
            count = count + 1;
            ingress_counters_0.write(meta.ingress_port_index, count);
        } else {
            bit<32> count;
            ingress_counters_1.read(count, meta.ingress_port_index);
            count = count + 1;
            ingress_counters_1.write(meta.ingress_port_index, count);
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

    // Register arrays for egress packet counting
    register<bit<32>>(2) egress_counters_0;
    register<bit<32>>(2) egress_counters_1;

    apply {
        // Calculate port index (0-based)
        meta.egress_port_index = (bit<32>)(standard_metadata.egress_port - 1);
        
        // Increment the appropriate counter based on active counter
        if ((bit<1>)meta.active_counter == 0) {
            bit<32> count;
            egress_counters_0.read(count, meta.egress_port_index);
            count = count + 1;
            egress_counters_0.write(meta.egress_port_index, count);
        } else {
            bit<32> count;
            egress_counters_1.read(count, meta.egress_port_index);
            count = count + 1;
            egress_counters_1.write(meta.egress_port_index, count);
        }

        // Set the ecn field (already 2 bits from metadata)
        hdr.ipv4.ecn = meta.active_counter;
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply { 
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version,
              hdr.ipv4.ihl,
              hdr.ipv4.dscp,
              hdr.ipv4.ecn,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
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