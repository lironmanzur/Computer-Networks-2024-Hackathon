import socket
import struct
import threading
import time
import select
from colorama import Fore, init

init(autoreset=True)

MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

def send_offer_messages(udp_port, tcp_port):
    """Broadcast UDP offers every second."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, udp_port, tcp_port)
    print(f"{Fore.GREEN}[SERVER] Broadcasting offers every second on UDP port {udp_port}")
    while True:
        try:
            sock.sendto(message, ('<broadcast>', udp_port))
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}[SERVER ERROR] Error broadcasting offers: {e}")

def handle_udp_request(server_socket, client_address, file_size):
    """Handle file transfer request over UDP."""
    try:
        print(f"{Fore.CYAN}[SERVER] Handling UDP request for {file_size} bytes from {client_address}")
        total_segments = (file_size + 1023) // 1024
        for segment in range(total_segments):
            payload = b'a' * min(1024, file_size - segment * 1024)
            message = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, total_segments, segment) + payload
            server_socket.sendto(message, client_address)
        print(f"{Fore.GREEN}[SERVER] Completed UDP transfer for {client_address}")
    except ConnectionResetError:
        print(f"{Fore.RED}[SERVER ERROR] Connection reset by peer for {client_address}")
    except Exception as e:
        print(f"{Fore.RED}[SERVER ERROR] UDP transfer error: {e}")

def handle_tcp_request(client_socket):
    """Handle file transfer request over TCP."""
    try:
        file_size = int(client_socket.recv(1024).decode().strip())
        print(f"{Fore.CYAN}[SERVER] Handling TCP request for {file_size} bytes")
        bytes_sent = 0
        while bytes_sent < file_size:
            chunk = b'a' * min(1024, file_size - bytes_sent)
            client_socket.sendall(chunk)
            bytes_sent += len(chunk)
        print(f"{Fore.GREEN}[SERVER] Completed TCP transfer: {bytes_sent} bytes")
    except Exception as e:
        print(f"{Fore.RED}[SERVER ERROR] TCP transfer error: {e}")
    finally:
        client_socket.close()

def main():
    udp_port = 15000
    tcp_port = 54321

    print(f"{Fore.GREEN}[SERVER] Starting server on UDP {udp_port} and TCP {tcp_port}")

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', udp_port))

    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind(('', tcp_port))
    tcp_socket.listen(5)

    threading.Thread(target=send_offer_messages, args=(udp_port, tcp_port), daemon=True).start()

    print(f"{Fore.GREEN}[SERVER] Server is ready to accept connections")

    while True:
        try:
            readable, _, _ = select.select([udp_socket, tcp_socket], [], [])
            for sock in readable:
                if sock is udp_socket:
                    try:
                        data, addr = udp_socket.recvfrom(2048)  # Buffer increased
                        if len(data) >= 13:
                            magic_cookie, message_type, file_size = struct.unpack('!IBQ', data[:13])
                            if magic_cookie == MAGIC_COOKIE and message_type == REQUEST_MESSAGE_TYPE:
                                threading.Thread(target=handle_udp_request, args=(udp_socket, addr, file_size), daemon=True).start()
                    except Exception as e:
                        print(f"{Fore.RED}[SERVER ERROR] Error handling UDP request: {e}")
                elif sock is tcp_socket:
                    try:
                        client_socket, addr = tcp_socket.accept()
                        threading.Thread(target=handle_tcp_request, args=(client_socket,), daemon=True).start()
                    except Exception as e:
                        print(f"{Fore.RED}[SERVER ERROR] Error accepting TCP connection: {e}")
        except Exception as e:
            print(f"{Fore.RED}[SERVER ERROR] Main loop error: {e}")

if __name__ == "__main__":
    main()
