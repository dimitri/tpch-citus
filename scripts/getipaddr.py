#! /usr/bin/env python3

# See
# https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib

import socket

def get_local_ip_list():
    iplist = []
    for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
        if not ip[2].startswith("127."):
            iplist.append(ip)

    return iplist

def get_ip_list_connecting():
    iplist = []
    for s in socket.socket(socket.AF_INET, socket.SOCK_DGRAM):
        s.connect(("8.8.8.8", 53))
        iplist.append(s.getsockname()[0])
        s.close()

    return iplist

if __name__ == '__main__':
    iplist = get_local_ip_list() or get_ip_list_connecting()

    if iplist:
        for ip in iplist:
            print(ip)
    else:
        print("no IP found")
