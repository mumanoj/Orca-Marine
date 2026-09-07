import sys
import socket
import ssl
import urllib.request

def debug_connection():
    host = "gateway.globalfishingwatch.org"
    port = 443
    print(f"1. DNS Lookup for {host}...")
    try:
        addrs = socket.getaddrinfo(host, port)
        print(f"Resolved IP addresses: {[a[4][0] for a in addrs]}")
    except Exception as e:
        print(f"DNS Resolution Failed: {e}")
        return

    print(f"\n2. Raw TCP Connection to {host}:{port}...")
    try:
        sock = socket.create_connection((host, port), timeout=10.0)
        print("TCP socket connected successfully!")
        
        print("\n3. SSL/TLS Handshake...")
        ctx = ssl.create_default_context()
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        print(f"SSL Handshake Success! Cipher: {ssl_sock.cipher()}, Version: {ssl_sock.version()}")
        ssl_sock.close()
    except Exception as e:
        print(f"TCP/SSL Connection Failed: {type(e).__name__} - {e}")

    print(f"\n4. urllib.request GET https://{host}/v3/datasets ...")
    try:
        req = urllib.request.Request(f"https://{host}/v3/datasets", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            print(f"urllib Status Code: {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"urllib HTTP Error: {e.code} - {e.reason}")
    except Exception as e:
        print(f"urllib Request Failed: {type(e).__name__} - {e}")

if __name__ == "__main__":
    debug_connection()
