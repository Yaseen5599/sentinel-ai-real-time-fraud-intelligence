"""
Sentinel AI — Supabase IPv6-to-IPv4 Loopback Bridge
Enables Docker containers (which lack IPv6 support on Docker Desktop macOS)
to reliably connect to direct Supabase PostgreSQL endpoints.
"""

import socket
import threading
import sys

TARGET_HOST = "db.ixrwbfvsoqkxzmnfsuuq.supabase.co"
TARGET_PORT = 6543
LISTEN_PORT = 6543

def handle_client(client_sock):
    try:
        addrinfo = socket.getaddrinfo(TARGET_HOST, TARGET_PORT, socket.AF_UNSPEC, socket.SOCK_STREAM)
        family, socktype, proto, _, sockaddr = addrinfo[0]
        
        target_sock = socket.socket(family, socktype, proto)
        target_sock.settimeout(10)
        target_sock.connect(sockaddr)
        target_sock.settimeout(None)
        client_sock.settimeout(None)
    except Exception as e:
        print(f"[Supabase Bridge] Connection error to {TARGET_HOST}:{TARGET_PORT} - {e}", flush=True)
        try:
            client_sock.close()
        except Exception:
            pass
        return

    def forward(src, dst):
        try:
            while True:
                data = src.recv(8192)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    threading.Thread(target=forward, args=(client_sock, target_sock), daemon=True).start()
    threading.Thread(target=forward, args=(target_sock, client_sock), daemon=True).start()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", LISTEN_PORT))
    except OSError as e:
        if e.errno == 48: # Address already in use
            print(f"[Supabase Bridge] Port {LISTEN_PORT} already bound and active.", flush=True)
            return
        raise
    server.listen(128)
    print(f"[Supabase Bridge] Active: listening on 0.0.0.0:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}", flush=True)
    while True:
        try:
            client_sock, _ = server.accept()
            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[Supabase Bridge] Accept error: {e}", flush=True)

if __name__ == "__main__":
    main()
