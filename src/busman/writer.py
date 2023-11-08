import socket

# Define the multicast group and port
multicast_group = '239.0.1.64'
port = 42069

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the socket to allow reusing the address
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to the desired interface and port
sock.bind(('0.0.0.0', port))

# Join the multicast group on the specified interface
group = socket.inet_aton(multicast_group)
mreq = group + socket.inet_aton('0.0.0.0')
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

# Now the socket is ready to send and receive multicast data
sock.sendto(b"Hello world", (multicast_group, port))
