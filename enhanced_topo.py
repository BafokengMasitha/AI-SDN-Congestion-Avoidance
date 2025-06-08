from mininet.topo import Topo

class EnhancedTopo(Topo):
    def build(self):
        # Hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        # Switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')  # Redundant path

        # Links (with bandwidth & delay)
        self.addLink(h1, s1, bw=10, delay='5ms')
        self.addLink(h2, s1, bw=10, delay='5ms')
        self.addLink(h3, s3, bw=10, delay='5ms')
        self.addLink(h4, s3, bw=10, delay='5ms')

        # Core mesh: multiple paths from s1 to s3
        self.addLink(s1, s2, bw=20, delay='1ms')
        self.addLink(s2, s3, bw=20, delay='1ms')
        self.addLink(s1, s4, bw=20, delay='2ms')
        self.addLink(s4, s3, bw=20, delay='2ms')
        self.addLink(s2, s4, bw=20, delay='3ms')

topos = {'enhancedtopo': (lambda: EnhancedTopo())}
