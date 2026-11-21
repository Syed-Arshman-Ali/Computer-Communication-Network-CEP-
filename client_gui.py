import socket
import time
import os
import tkinter as tk
from tkinter import scrolledtext, filedialog

XOR_KEY = 42

def xor_cipher(data: bytes, key: int = XOR_KEY) -> bytes:
    return bytes([b ^ key for b in data])

class AuraNetClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AURA-NET Client Node")
        self.root.geometry("640x600")
        self.root.configure(bg="#121212")

        self.persistent_sock = None
        self.connected_target = None

        # Top Input Frame
        input_frame = tk.Frame(root, bg="#121212")
        input_frame.pack(pady=15)

        tk.Label(input_frame, text="Target IP:", fg="#00e676", bg="#121212", font=("Consolas", 10, "bold")).grid(row=0, column=0, padx=5)
        self.ip_entry = tk.Entry(input_frame, width=18, bg="#262626", fg="white", insertbackground="white", font=("Consolas", 10))
        self.ip_entry.insert(0, "192.168.18.102")
        self.ip_entry.grid(row=0, column=1, padx=5)

        tk.Label(input_frame, text="Port:", fg="#00e676", bg="#121212", font=("Consolas", 10, "bold")).grid(row=0, column=2, padx=5)
        self.port_entry = tk.Entry(input_frame, width=7, bg="#262626", fg="white", insertbackground="white", font=("Consolas", 10))
        self.port_entry.insert(0, "8888")
        self.port_entry.grid(row=0, column=3, padx=5)

        tk.Label(input_frame, text="File Path:", fg="#00e676", bg="#121212", font=("Consolas", 10, "bold")).grid(row=1, column=0, padx=5, pady=10)
        self.path_entry = tk.Entry(input_frame, width=32, bg="#262626", fg="white", insertbackground="white", font=("Consolas", 10))
        self.path_entry.insert(0, "/index.html")
        self.path_entry.grid(row=1, column=1, columnspan=3, sticky="w", padx=5, pady=10)

        # Freshness Mode
        self.freshness_var = tk.StringVar(value="force")
        tk.Radiobutton(root, text="Force Download (Past Timestamp)", variable=self.freshness_var, value="force",
                       fg="white", bg="#121212", selectcolor="#333333", font=("Consolas", 9)).pack()
        tk.Radiobutton(root, text="Check Freshness (Future Timestamp)", variable=self.freshness_var, value="fresh",
                       fg="white", bg="#121212", selectcolor="#333333", font=("Consolas", 9)).pack()

        # Connection Mode
        tk.Label(root, text="--- Connection Mode ---", fg="#888888", bg="#121212", font=("Consolas", 9)).pack(pady=(12, 4))
        self.mode_var = tk.StringVar(value="Retain")
        tk.Radiobutton(root, text="Non-Persistent (Sever - Slower)", variable=self.mode_var, value="Sever",
                       fg="#ff5252", bg="#121212", selectcolor="#333333", font=("Consolas", 9)).pack()
        tk.Radiobutton(root, text="Persistent (Retain - Faster)", variable=self.mode_var, value="Retain",
                       fg="#00e676", bg="#121212", selectcolor="#333333", font=("Consolas", 9)).pack()

        # Action Buttons
        btn_frame = tk.Frame(root, bg="#121212")
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="TRANSMIT PULL-OBJECT", command=self.send_request,
                  bg="#4a148c", fg="white", font=("Consolas", 10, "bold"), padx=12, pady=6, relief="flat").grid(row=0, column=0, padx=8)

        tk.Button(btn_frame, text="UPLOAD FILE (PUSH-OBJECT)", command=self.upload_file,
                  bg="#1b5e20", fg="white", font=("Consolas", 10, "bold"), padx=12, pady=6, relief="flat").grid(row=0, column=1, padx=8)

        # Output Console
        self.output = scrolledtext.ScrolledText(root, width=72, height=18, bg="#000000", fg="#00e676", font=("Consolas", 9))
        self.output.pack(padx=15, pady=5)

    def close_persistent(self):
        if self.persistent_sock:
            try:
                self.persistent_sock.close()
            except Exception:
                pass
            self.persistent_sock = None
            self.connected_target = None

    def get_socket(self, target_ip, target_port, mode):
        if mode == "Retain" and self.persistent_sock and self.connected_target == (target_ip, target_port):
            return self.persistent_sock
        self.close_persistent()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((target_ip, target_port))
        if mode == "Retain":
            self.persistent_sock = sock
            self.connected_target = (target_ip, target_port)
        return sock

    def upload_file(self):
        local_path = filedialog.askopenfilename(title="Select file to upload via AURA-NET")
        if not local_path:
            return

        target_ip = self.ip_entry.get().strip()
        target_port = int(self.port_entry.get().strip())
        mode = self.mode_var.get()
        file_name = os.path.basename(local_path)

        with open(local_path, 'rb') as f:
            raw_bytes = f.read()

        encrypted_payload = xor_cipher(raw_bytes)
        header = (
            f"PUSH-OBJECT /{file_name} AURA-NET/1.0\r\n"
            f"Host: {target_ip}\r\n"
            f"Cipher-Mask: XOR-Active\r\n"
            f"Stream-Mode: {mode}\r\n"
            f"Content-Length: {len(encrypted_payload)}\r\n\r\n"
        ).encode('utf-8')

        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, f"[*] Uploading '{file_name}' ({len(raw_bytes)} bytes, XOR-encrypted)...\n\n")

        start_time = time.perf_counter()
        try:
            sock = self.get_socket(target_ip, target_port, mode)
            sock.sendall(header + encrypted_payload)
            response = sock.recv(4096)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            header_text = response.decode('utf-8', errors='ignore').strip()
            self.output.insert(tk.END, "--- AURA-NET RESPONSE HEADER ---\n")
            self.output.insert(tk.END, f"{header_text}\n\n")
            self.output.insert(tk.END, f"[NETWORK TIMER] Total Upload Time: {elapsed_ms:.2f} ms\n\n")

            if "200 STORED" in header_text:
                self.output.insert(tk.END, f"[+] 200 STORED: '{file_name}' saved on Origin & stale proxy cache invalidated.\n")
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, f"/{file_name}")

            if mode == "Sever":
                sock.close()
                self.close_persistent()
        except Exception as e:
            self.close_persistent()
            self.output.insert(tk.END, f"[!] Upload Error: {e}\n")

    def send_request(self):
        target_ip = self.ip_entry.get().strip()
        target_port = int(self.port_entry.get().strip())
        file_path = self.path_entry.get().strip()
        if not file_path.startswith('/'):
            file_path = '/' + file_path

        mode = self.mode_var.get()
        timestamp = 0 if self.freshness_var.get() == "force" else time.time() + 10000

        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, f"[*] Initializing fetch... (Mode: {mode})\n\n")

        request = (
            f"PULL-OBJECT {file_path} AURA-NET/1.0\r\n"
            f"Host: {target_ip}\r\n"
            f"Cipher-Mask: XOR-Active\r\n"
            f"Stream-Mode: {mode}\r\n"
            f"Last-Birth-Clock: {timestamp}\r\n\r\n"
        ).encode('utf-8')

        start_time = time.perf_counter()

        try:
            sock = self.get_socket(target_ip, target_port, mode)
            sock.sendall(request)
            response = sock.recv(5242880)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if not response:
                self.close_persistent()
                self.output.insert(tk.END, "[!] Connection closed by proxy.\n")
                return

            if b"\r\n\r\n" in response:
                header_bytes, payload_bytes = response.split(b"\r\n\r\n", 1)
            else:
                header_bytes, payload_bytes = response, b""

            header_text = header_bytes.decode('utf-8', errors='ignore')
            self.output.insert(tk.END, "--- AURA-NET RESPONSE HEADER ---\n")
            self.output.insert(tk.END, f"{header_text}\n\n")
            self.output.insert(tk.END, f"[NETWORK TIMER] Total Fetch Time: {elapsed_ms:.2f} ms\n\n")

            if "404 GHOST" in header_text:
                self.output.insert(tk.END, "[!] 404 GHOST: File not found on network.\n")
                self.close_persistent()
            elif "102 STILL-FRESH" in header_text:
                self.output.insert(tk.END, "[+] 102 STILL-FRESH: Local copy is up-to-date. 0 payload bytes transferred.\n")
            elif payload_bytes:
                decrypted = xor_cipher(payload_bytes)
                try:
                    decoded_text = decrypted.decode('utf-8')
                    self.output.insert(tk.END, "--- DECRYPTED PAYLOAD ---\n")
                    self.output.insert(tk.END, decoded_text + "\n")
                except UnicodeDecodeError:
                    save_name = "received_" + os.path.basename(file_path)
                    with open(save_name, 'wb') as f:
                        f.write(decrypted)
                    self.output.insert(tk.END, f"[+] Binary payload detected & decrypted! Saved safely to disk as '{save_name}' ({len(decrypted)} bytes).\n")

            if mode == "Sever":
                sock.close()
                self.close_persistent()

        except Exception as e:
            self.close_persistent()
            self.output.insert(tk.END, f"[!] Network Error: {e}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = AuraNetClientGUI(root)
    root.mainloop()