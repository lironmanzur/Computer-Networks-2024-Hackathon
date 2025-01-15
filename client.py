import socket
import struct
import threading
import time
from colorama import Fore, init

init(autoreset=True)

MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3

def listen_for_offers(udp_port, offer_event, server_info):
    """Listen for server offers using UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', udp_port))

    print(f"{Fore.BLUE}[CLIENT] Listening for offers on UDP port {udp_port}")
    while not offer_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)  # Buffer increased
            if len(data) >= 9:
                magic_cookie, message_type, server_udp_port, server_tcp_port = struct.unpack('!IBHH', data[:9])
                if magic_cookie == MAGIC_COOKIE and message_type == OFFER_MESSAGE_TYPE:
                    server_info.update({
                        'udp_port': server_udp_port,
                        'tcp_port': server_tcp_port,
                        'address': addr[0]
                    })
                    offer_event.set()
        except Exception as e:
            print(f"{Fore.RED}[CLIENT ERROR] Error while listening for offers: {e}")

def send_tcp_request(server_info, file_size):
    """Send a file size request using TCP and receive the data."""
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((server_info['address'], server_info['tcp_port']))
        tcp_socket.sendall(f"{file_size}\n".encode())

        bytes_received = 0
        start_time = time.time()
        while bytes_received < file_size:
            data = tcp_socket.recv(2048)  # Buffer increased
            if not data:
                break
            bytes_received += len(data)

        elapsed_time = time.time() - start_time
        speed = (bytes_received * 8) / elapsed_time
        print(f"{Fore.GREEN}[CLIENT] TCP transfer completed: {bytes_received}/{file_size} bytes in {elapsed_time:.2f}s ({speed:.2f} bps)")
    except Exception as e:
        print(f"{Fore.RED}[CLIENT ERROR] TCP error: {e}")

def send_udp_request(server_info, file_size):
    """Send a UDP file request and receive the file."""
    try:
        message = struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, file_size)
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(message, (server_info['address'], server_info['udp_port']))

        start_time = time.time()
        segments_received = 0

        udp_socket.settimeout(5.0)  # Increased timeout for larger files
        while True:
            try:
                data, _ = udp_socket.recvfrom(2048)  # Buffer increased
                segments_received += 1
            except socket.timeout:
                break

        elapsed_time = time.time() - start_time
        total_bytes = segments_received * 1024
        speed = (segments_received * 1024 * 8) / elapsed_time
        print(f"{Fore.GREEN}[CLIENT] UDP transfer completed: {total_bytes}/{file_size} bytes in {elapsed_time:.2f}s ({speed:.2f} bps)")
    except Exception as e:
        print(f"{Fore.RED}[CLIENT ERROR] {e}")

def main():
    udp_port = 15000

    while True:
        try:
            file_size = int(input("Enter the file size to download (in bytes): ").strip())
            if file_size <= 0:
                raise ValueError("File size must be a positive integer.")
            tcp_connections = int(input("Enter the number of TCP connections: ").strip())
            udp_connections = int(input("Enter the number of UDP connections: ").strip())
            if tcp_connections <= 0 or udp_connections <= 0:
                raise ValueError("Connection counts must be positive integers.")
        except ValueError as e:
            print(f"{Fore.RED}[CLIENT ERROR] Invalid input: {e}")
            continue

        offer_event = threading.Event()
        server_info = {}

        threading.Thread(target=listen_for_offers, args=(udp_port, offer_event, server_info), daemon=True).start()

        print(f"{Fore.BLUE}[CLIENT] Looking for server...")
        offer_event.wait()
        print(f"{Fore.BLUE}[CLIENT] Connected to server at {server_info['address']}")

        threads = []
        for _ in range(tcp_connections):
            thread = threading.Thread(target=send_tcp_request, args=(server_info, file_size), daemon=True)
            threads.append(thread)
            thread.start()

        for _ in range(udp_connections):
            thread = threading.Thread(target=send_udp_request, args=(server_info, file_size), daemon=True)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()  # Wait for all threads to finish

        print(f"{Fore.BLUE}[CLIENT] Transfers complete. Returning to search for offers...\n")

if __name__ == "__main__":
    main()
