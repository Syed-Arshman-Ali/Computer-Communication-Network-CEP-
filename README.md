# AURA-NET/1.0: Custom Application-Layer Protocol & Proxy Network

**AURA-NET/1.0** is a lightweight, highly optimized custom application-layer protocol engineered from scratch using Python TCP sockets. Developed as a Complex Engineering Problem (CEP) for the CS-327 Computer Communication Networks course at NED University, this project bypasses traditional HTTP to demonstrate low-level packet construction, cryptographic security, and advanced bandwidth optimization.

The architecture simulates a modern Content Delivery Network (CDN) utilizing a 3-tier node distribution model deployed across a Local Area Network (LAN) and a Tailscale Mesh VPN.

## 🚀 Key Engineering Features

* **Custom Protocol Semantics:** Implements the custom `PULL-OBJECT` verb and a specialized header architecture parsed purely via `\r\n` CRLF delimiters.
* **Intelligent Edge Caching:** A dedicated Caching Proxy intercepts client requests, storing encrypted payloads locally (`101 VAULT-HIT`) to drastically reduce Origin Server load.
* **Bandwidth Optimization (102 STILL-FRESH):** The protocol uses high-precision Unix timestamps (`Last-Birth-Clock`). If the client's cached file is up-to-date, the Origin Server drops the heavy payload and only sends a 40-byte header, saving 99.99% of transmission bandwidth.
* **TCP Socket Persistence:** Implements a `Stream-Mode: Retain/Sever` toggle. Reusing the TCP socket for multiple requests bypasses the 3-way handshake overhead, dropping application-level latency from 15.42 ms to 3.38 ms.
* **Cryptography at Rest & in Transit:** All payloads (UTF-8 text and high-res binary JPEGs) are scrambled using a Bitwise XOR Cipher before leaving the Origin Server, ensuring intermediary nodes cannot read the data.
* **Universal GUI Client:** A Tkinter-based dashboard that handles custom header construction, network latency timing, decryption, and secure binary-file writing (preventing `UnicodeDecodeError` crashes).

## 📡 Protocol Specification

AURA-NET/1.0 utilizes strict ASCII header formatting. A standard request looks like this:

```http
PULL-OBJECT /datapath.jpeg AURA-NET/1.0
Host: 192.168.18.101
Cipher-Mask: XOR-Active
Stream-Mode: Retain
Last-Birth-Clock: 1794615426.6515539
```

### 🚦 Custom Status Codes

* **`100 DELIVERED`**: Cache Miss. Origin fetched, encrypted, and attached the full payload.
* **`101 VAULT-HIT`**: Proxy served the encrypted file directly from local cache.
* **`102 STILL-FRESH`**: File unmodified. Origin drops payload to save bandwidth.
* **`404 GHOST`**: Object missing on the Origin. Connection terminated safely.

## ⚙️ System Architecture

* **🖥️ Host A (Origin Server):** Binds to Port `8080`. Multithreaded daemon architecture to handle concurrent clients without blocking.
* **⚙️ Host A (Caching Proxy):** Binds to Port `8888`. Intercepts client traffic, manages the `cache/` directory, and routes cache misses to the Origin.
* **💻 Host B (Client GUI):** The end-user interface that decrypts and displays the payload.

## 💻 How to Run

1. Clone the repository and ensure you have Python 3.x installed.
2. Create a folder named `cache` in the same directory as the proxy script.
3. Start the Origin Server:

   ```bash
   python main.py

4. Start the Caching Proxy:

   ```bash
   python proxy.py

5. Launch the Client GUI::

   ```bash
   python client_gui.py

6. Enter the target IP address of the Proxy, specify a file (e.g., `/index.html` or `/datapath.jpeg`), and hit **Transmit PULL-OBJECT**.

## 👥 Project Team

* **Syed Arshman Ali Shah (Lead):** Origin Server Architecture, Proxy Logic, XOR Cryptography.
* **Mair Nasir:** Client Tkinter GUI, Binary Exception Handling, LAN/VPN Deployment.
* **Syed Ramish Akhter:** Wireshark Packet Analysis, Network Topology, Documentation.
* **Siraj Ul Haq:** TCP Performance Metrics, Bandwidth Reductions, Failure Validation.

   
