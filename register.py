import socket

def get_ip_address(location):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    domain, port = location.split(':')
    s.connect((domain, int(port)))
    return s.getsockname()[0]