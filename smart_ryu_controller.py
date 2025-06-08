from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, arp
from ryu.lib.packet import ether_types
from collections import defaultdict


class SmartSDN(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SmartSDN, self).__init__(*args, **kwargs)
        self.mac_to_port = defaultdict(dict)  # {dpid: {mac: port}}
        self.arp_table = {}  # {ip: mac}
        self.switches = set()  # Track all connected switches

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.switches.add(datapath.id)

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        print(f"[Init] Installed table-miss flow for switch {datapath.id}")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                           actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath,
                                  buffer_id=buffer_id,
                                  priority=priority,
                                  match=match,
                                  instructions=inst,
                                  idle_timeout=idle_timeout,
                                  hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath,
                                  priority=priority,
                                  match=match,
                                  instructions=inst,
                                  idle_timeout=idle_timeout,
                                  hard_timeout=hard_timeout)
        datapath.send_msg(mod)
        print(f"[Flow] Added flow on switch {datapath.id}: match={match}, actions={actions}")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        # Learn MAC address (per-switch learning)
        self.mac_to_port[dpid][src] = in_port
        print(f"[MAC->Port] Switch {dpid} learned {src} on port {in_port}")
        print(f"[MAC->Port] Current table for switch {dpid}: {self.mac_to_port[dpid]}")

        # Handle ARP packets
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self.handle_arp(datapath, pkt, eth, arp_pkt, in_port)
            return

        # Handle other packets (IPv4, etc.)
        self.handle_other_packets(datapath, msg, eth, in_port, src, dst)

    def handle_arp(self, datapath, pkt, eth, arp_pkt, in_port):
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        src_ip = arp_pkt.src_ip
        dst_ip = arp_pkt.dst_ip
        src_mac = arp_pkt.src_mac

        # Update ARP table and MAC-to-port mapping
        self.arp_table[src_ip] = src_mac
        self.mac_to_port[dpid][src_mac] = in_port

        print(f'[ARP] ARP {arp_pkt.opcode} from {src_ip} ({src_mac}) to {dst_ip} on switch {dpid} port {in_port}')
        print(f'[ARP] ARP table: {self.arp_table}')
        print(f'[MAC->Port] Current table for switch {dpid}: {self.mac_to_port[dpid]}')

        if arp_pkt.opcode == arp.ARP_REQUEST:
            if dst_ip in self.arp_table:
                # We know the destination MAC - send ARP reply
                dst_mac = self.arp_table[dst_ip]
                self.send_arp_reply(datapath, src_mac, src_ip, dst_mac, dst_ip, in_port)
            else:
                # Flood ARP request to all ports except incoming port
                self.flood_packet(datapath, in_port, pkt.data)
        elif arp_pkt.opcode == arp.ARP_REPLY:
            # Learn the MAC address from ARP reply
            self.mac_to_port[dpid][src_mac] = in_port
            # Forward to the appropriate port if we know it
            if dst_mac in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst_mac]
                actions = [parser.OFPActionOutput(out_port)]
                self.send_packet_out(datapath, in_port, actions, pkt.data)
            else:
                self.flood_packet(datapath, in_port, pkt.data)

    def handle_other_packets(self, datapath, msg, eth, in_port, src, dst):
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Check if destination MAC is known on this switch
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            actions = [parser.OFPActionOutput(out_port)]
            
            # Install flow only for unicast traffic
            if not self.is_multicast(dst):
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
                # Set idle timeout to allow for MAC address changes
                self.add_flow(datapath, 1, match, actions, msg.buffer_id, idle_timeout=10)
                
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    return
        else:
            # Flood for unknown unicast or multicast/broadcast
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        self.send_packet_out(datapath, in_port, actions, msg.data)

    def send_arp_reply(self, datapath, src_mac, src_ip, dst_mac, dst_ip, out_port):
        ofproto = datapath.ofproto  # Add this line to get ofproto from datapath
        parser = datapath.ofproto_parser
        
        arp_reply = packet.Packet()
        arp_reply.add_protocol(ethernet.ethernet(
            ethertype=ether_types.ETH_TYPE_ARP,
            dst=src_mac,
            src=dst_mac))
        arp_reply.add_protocol(arp.arp(
            opcode=arp.ARP_REPLY,
            src_mac=dst_mac,
            src_ip=dst_ip,
            dst_mac=src_mac,
            dst_ip=src_ip))
        arp_reply.serialize()

        actions = [parser.OFPActionOutput(out_port)]
        self.send_packet_out(datapath, ofproto.OFPP_CONTROLLER, actions, arp_reply.data)
        print(f'[ARP] Sent ARP reply for {dst_ip} ({dst_mac}) to {src_ip}')
    def flood_packet(self, datapath, in_port, data):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.send_packet_out(datapath, in_port, actions, data)

    def send_packet_out(self, datapath, in_port, actions, data):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=data)
        datapath.send_msg(out)

    def is_multicast(self, mac):
        # Check if MAC is multicast/broadcast
        return (mac.startswith('01:00:5e:') or 
                mac.startswith('33:33:') or 
                mac == 'ff:ff:ff:ff:ff:ff')