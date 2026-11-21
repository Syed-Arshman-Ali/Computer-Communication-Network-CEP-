import socket
import threading
import os

HOST = '0.0.0.0'
PORT = 8888
ORIGIN_IP = '192.168.18.101'  # <--- CHANGE THIS TO DEVICE 1's IP ADDRESS
ORIGIN_PORT = 8080
CACHE_DIR = 'cache'

os.makedirs(CACHE_DIR, exist_ok=True)

def recv_message(conn):
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        chunk = conn.recv(4096)
        if not chunk:
            return None, None
        buffer += chunk

    header_bytes, body = buffer.split(b"\r\n\r\n", 1)
    header_text = header_bytes.decode('utf-8', errors='ignore')

    content_length = 0
    for line in header_text.split('\r\n')[1:]:
        if line.lower().startswith("content-length:"):
            content_length = int(line.split(':', 1)[1].strip())

    while len(body) < content_length:
        chunk = conn.recv(min(65536, content_length - len(body)))
        if not chunk:
            break
        body += chunk

    return header_text, body

def forward_to_origin(raw_data: bytes) -> bytes:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as origin_sock:
        origin_sock.settimeout(10)
        origin_sock.connect((ORIGIN_IP, ORIGIN_PORT))
        origin_sock.sendall(raw_data)

        chunks = []
        while True:
            try:
                data = origin_sock.recv(5242880)
                if not data:
                    break
                chunks.append(data)
            except socket.timeout:
                break
        return b"".join(chunks)

def handle_client(conn, addr):
    try:
        while True:
            header_text, body = recv_message(conn)
            if header_text is None:
                break

            lines = header_text.split('\r\n')
            parts = lines[0].split()
            if len(parts) < 2:
                break

            verb = parts[0]
            file_name = os.path.basename(parts[1].lstrip('/')) or "index.html"
            cache_path = os.path.join(CACHE_DIR, file_name)

            print(f"[*] Proxy Intercepted: {lines[0]}")

            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip()] = v.strip()

            stream_mode = headers.get("Stream-Mode", "Sever")

            # --- HANDLE UPLOAD (PUSH-OBJECT) + CACHE INVALIDATION ---
            if verb == "PUSH-OBJECT":
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    print(f"[*] CACHE INVALIDATED: Removed stale '{file_name}' from proxy cache.")

                origin_header = header_text.replace("Stream-Mode: Retain", "Stream-Mode: Sever")
                origin_response = forward_to_origin(origin_header.encode('utf-8') + b"\r\n\r\n" + body)
                final_resp = origin_response.replace(b"Stream-Mode: Sever", f"Stream-Mode: {stream_mode}".encode('utf-8'))
                conn.sendall(final_resp)

            # --- HANDLE DOWNLOAD (PULL-OBJECT) ---
            elif verb == "PULL-OBJECT":
                last_birth_clock = float(headers.get("Last-Birth-Clock", 0))

                if last_birth_clock > 0 and os.path.exists(cache_path):
                    origin_header = header_text.replace("Stream-Mode: Retain", "Stream-Mode: Sever")
                    origin_response = forward_to_origin(origin_header.encode('utf-8') + b"\r\n\r\n")
                    if b"102 STILL-FRESH" in origin_response:
                        resp = origin_response.replace(b"Stream-Mode: Sever", f"Stream-Mode: {stream_mode}".encode('utf-8'))
                        conn.sendall(resp)
                        if stream_mode == "Sever":
                            break
                        continue

                if os.path.exists(cache_path):
                    print(f"[*] VAULT-HIT: Serving encrypted '{file_name}' from proxy cache.")
                    with open(cache_path, 'rb') as f:
                        encrypted_payload = f.read()

                    header = (
                        f"AURA-NET/1.0 101 VAULT-HIT\r\n"
                        f"Stream-Mode: {stream_mode}\r\n"
                        f"Cipher-Mask: XOR-Active\r\n\r\n"
                    ).encode('utf-8')
                    conn.sendall(header + encrypted_payload)
                else:
                    print(f"[*] CACHE MISS: Requesting '{file_name}' from Origin ({ORIGIN_IP}:{ORIGIN_PORT}).")
                    origin_header = header_text.replace("Stream-Mode: Retain", "Stream-Mode: Sever")
                    origin_response = forward_to_origin(origin_header.encode('utf-8') + b"\r\n\r\n")

                    if b"100 DELIVERED" in origin_response and b"\r\n\r\n" in origin_response:
                        _, encrypted_payload = origin_response.split(b"\r\n\r\n", 1)
                        with open(cache_path, 'wb') as f:
                            f.write(encrypted_payload)
                        print(f"[*] Saved encrypted '{file_name}' to proxy cache.")

                    final_resp = origin_response.replace(b"Stream-Mode: Sever", f"Stream-Mode: {stream_mode}".encode('utf-8'))
                    conn.sendall(final_resp)

                    if b"404 GHOST" in origin_response:
                        break
            else:
                break

            if stream_mode == "Sever":
                break
    except Exception as e:
        print(f"[!] Proxy Error ({addr}): {e}")
    finally:
        conn.close()

def start_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)
    print(f"[*] AURA-NET Proxy running on {HOST}:{PORT} -> Forwarding to {ORIGIN_IP}:{ORIGIN_PORT}")

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    start_proxy()