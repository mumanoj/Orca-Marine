import sys
sys.path.insert(0, ".")
import os
import socket
import ssl
import json
from app.core.config import settings

def test_raw_socket():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING RAW SSL SOCKET TO GFW ===")
    
    hostname = 'gateway.globalfishingwatch.org'
    port = 443

    ctx = ssl.create_default_context()
    ctx.check_hostname = True

    try:
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                print("SSL Handshake Successful! Cipher:", ssock.cipher())
                print("TLS Version:", ssock.version())

                request = (
                    f"GET /v3/vessels/search?query=india&limit=5 HTTP/1.1\r\n"
                    f"Host: {hostname}\r\n"
                    f"Authorization: Bearer {gfw_key}\r\n"
                    f"User-Agent: ORCA-Platform/1.0\r\n"
                    f"Accept: application/json\r\n"
                    f"Connection: close\r\n\r\n"
                )
                ssock.sendall(request.encode('utf-8'))
                
                response = b""
                while True:
                    data = ssock.recv(4096)
                    if not data:
                        break
                    response += data
                
                res_str = response.decode('utf-8', errors='ignore')
                status_line = res_str.split('\r\n')[0]
                print("Response Status:", status_line)
                headers_and_body = res_str.split('\r\n\r\n', 1)
                if len(headers_and_body) > 1:
                    body = headers_and_body[1]
                    print("[SUCCESS] Raw GFW API Body (first 400 chars):")
                    print(body[:400])
                    try:
                        parsed = json.loads(body)
                        print("Parsed Json Keys:", list(parsed.keys()) if isinstance(parsed, dict) else len(parsed))
                    except Exception as pe:
                        pass
    except Exception as e:
        print("Socket Exception:", type(e).__name__, ":", e)

if __name__ == "__main__":
    test_raw_socket()
