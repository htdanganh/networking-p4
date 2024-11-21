from p4utils.mininetlib.network_API import NetworkAPI

net = NetworkAPI()

# Network general options
net.setLogLevel('info')
net.setCompiler(p4rt=True)
net.enableCli()

# Network definition
net.addP4RuntimeSwitch('s1')
net.addP4RuntimeSwitch('s2')
net.addP4RuntimeSwitch('s3')
net.addP4RuntimeSwitch('s4')

net.setP4Source('s1','detector.p4')
net.setP4Source('s2','detector.p4')
net.setP4Source('s3','detector.p4')
net.setP4Source('s4','detector.p4')

net.addHost('h1')
net.addHost('h2')
# Host to switch links
net.addLink('s1', 'h1')
net.addLink('s3', 'h2')
# Switch to switch link
net.addLink('s1', 's2')
net.addLink('s2', 's3')
net.addLink('s4', 's3')
net.addLink('s4', 's1')

# Assignment strategy
net.l2()

# Nodes general options
# net.enablePcapDumpAll()
# net.enableLogAll()
net.disablePcapDumpAll()
net.disableLogAll()
# Start network
net.startNetwork()
