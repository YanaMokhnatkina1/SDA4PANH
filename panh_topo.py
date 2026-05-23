#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

class PANHHighAvailabilityTopo(Topo):
    def build(self):
        r1 = self.addNode('r1', cls=LinuxRouter, ip='10.1.10.1/24')
        r3 = self.addNode('r3', cls=LinuxRouter, ip='10.1.10.2/24')
        r2 = self.addNode('r2', cls=LinuxRouter, ip='10.2.10.1/24')

        s_hq = self.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')
        s_br = self.addSwitch('s2', cls=OVSKernelSwitch, failMode='standalone')

        h_srv = self.addHost('hsrv', ip='10.1.10.10/24', defaultRoute='via 10.1.10.1')
        h_meteo = self.addHost('hmeteo', ip='10.2.10.10/24', defaultRoute='via 10.2.10.1')

        self.addLink(h_srv, s_hq)
        self.addLink(s_hq, r1, intfName2='r1-eth0', params2={'ip': '10.1.10.1/24'})
        self.addLink(s_hq, r3, intfName2='r3-eth0', params2={'ip': '10.1.10.2/24'})

        self.addLink(h_meteo, s_br)
        self.addLink(s_br, r2, intfName2='r2-eth0', params2={'ip': '10.2.10.1/24'})

        self.addLink(r1, r3, intfName1='r1-int1', intfName2='r3-int1',
                     params1={'ip': '172.16.1.1/30'}, params2={'ip': '172.16.1.2/30'},
                     bw=1000, delay='1ms', use_htb=True)

        self.addLink(r1, r3, intfName1='r1-int2', intfName2='r3-int2',
                     params1={'ip': '172.16.2.1/30'}, params2={'ip': '172.16.2.2/30'},
                     bw=1000, delay='1ms', use_htb=True)

        self.addLink(r1, r2, intfName1='r1-eth1', intfName2='r2-eth1',
                     params1={'ip': '192.168.1.1/30'}, params2={'ip': '192.168.1.2/30'},
                     bw=100, delay='10ms', use_htb=True)

        self.addLink(r3, r2, intfName1='r3-eth2', intfName2='r2-eth2',
                     params1={'ip': '192.168.2.1/30'}, params2={'ip': '192.168.2.2/30'},
                     bw=30, delay='40ms', use_htb=True)

        self.addLink(r3, r2, intfName1='r3-eth3', intfName2='r2-eth3',
                     params1={'ip': '192.168.3.1/30'}, params2={'ip': '192.168.3.2/30'},
                     bw=10, delay='500ms', use_htb=True)

def run():
    topo = PANHHighAvailabilityTopo()
    net = Mininet(topo=topo, link=TCLink, controller=None)
    
    print("*** Starting resilient L3 network for JSC NPC PANH...")
    net.start()
    
    r1, r2, r3 = net.get('r1', 'r2', 'r3')
    
    for r in [r1, r2, r3]:
        r.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0')
        r.cmd('sysctl -w net.ipv4.conf.default.rp_filter=0')
        for intf in r.intfList():
            r.cmd('sysctl -w net.ipv4.conf.{}.rp_filter=0'.format(intf.name))
    
    r1.cmd('ip route add 10.2.10.0/24 via 192.168.1.2 dev r1-eth1 metric 10')
    r1.cmd('ip route add 10.2.10.0/24 via 172.16.1.2 dev r1-int1 metric 50')
    r1.cmd('ip route add 10.2.10.0/24 via 172.16.2.2 dev r1-int2 metric 55')
    
    r3.cmd('ip route add 10.2.10.0/24 via 192.168.2.2 dev r3-eth2 metric 10')
    r3.cmd('ip route add 10.2.10.0/24 via 192.168.3.2 dev r3-eth3 metric 60')
    r3.cmd('ip route add 10.2.10.0/24 via 172.16.1.1 dev r3-int1 metric 100')
    
    r2.cmd('ip route add 10.1.10.0/24 via 192.168.1.1 dev r2-eth1 metric 10')
    r2.cmd('ip route add 10.1.10.0/24 via 192.168.2.1 dev r2-eth2 metric 50')
    r2.cmd('ip route add 10.1.10.0/24 via 192.168.3.1 dev r2-eth3 metric 100')

    print("*** Network is ready. Internal cross-links are active.")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()