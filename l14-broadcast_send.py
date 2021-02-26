import socket
import argparse


def run(group, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto('broadcast test'.encode(), (group, port))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bcast-group', default='192.168.11.255')
    parser.add_argument('--port', default=19900)
    args = parser.parse_args()
    run(args.bcast_group, args.port)