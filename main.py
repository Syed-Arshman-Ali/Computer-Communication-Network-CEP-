import socket
import threading
import os

HOST = '0.0.0.0'
PORT = 8080
XOR_KEY = 42

def xor_cipher(data: bytes, key: int = XOR_KEY) -> bytes:
    return bytes([b ^ key for b in data])

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

def handle_client(conn, addr):
    print(f"[+] Origin connected to {addr}")
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

            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip()] = v.strip()

            stream_mode = headers.get("Stream-Mode", "Sever")

            # --- HANDLE UPLOAD (PUSH-OBJECT) ---
            if verb == "PUSH-OBJECT":
                decrypted_data = xor_cipher(body)
                with open(file_name, 'wb') as f:
                    f.write(decrypted_data)
                print(f"[*] PUSH-OBJECT: Decrypted & stored '{file_name}' ({len(decrypted_data)} bytes).")

                response = (
                    f"AURA-NET/1.0 200 STORED\r\n"
                    f"Stream-Mode: {stream_mode}\r\n\r\n"
                ).encode('utf-8')
                conn.sendall(response)

            # --- HANDLE DOWNLOAD (PULL-OBJECT) ---
            elif verb == "PULL-OBJECT":
                last_birth_clock = float(headers.get("Last-Birth-Clock", 0))

                if not os.path.exists(file_name):
                    response = (
                        f"AURA-NET/1.0 404 GHOST\r\n"
                        f"Stream-Mode: Sever\r\n\r\n"
                    ).encode('utf-8')
                    conn.sendall(response)
                    break

                file_mtime = os.path.getmtime(file_name)

                if last_birth_clock >= file_mtime:
                    response = (
                        f"AURA-NET/1.0 102 STILL-FRESH\r\n"
                        f"Stream-Mode: {stream_mode}\r\n\r\n"
                    ).encode('utf-8')
                    conn.sendall(response)
                else:
                    with open(file_name, 'rb') as f:
                        raw_payload = f.read()

                    encrypted_payload = xor_cipher(raw_payload)
                    header = (
                        f"AURA-NET/1.0 100 DELIVERED\r\n"
                        f"Stream-Mode: {stream_mode}\r\n"
                        f"Cipher-Mask: XOR-Active\r\n\r\n"
                    ).encode('utf-8')
                    conn.sendall(header + encrypted_payload)
            else:
                break

            if stream_mode == "Sever":
                break
    except Exception as e:
        print(f"[!] Origin Error ({addr}): {e}")
    finally:
        conn.close()

def start_origin():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)
    print(f"[*] AURA-NET Origin Server running on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    start_origin()