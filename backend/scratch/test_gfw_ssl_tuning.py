import sys
import socket
import ssl
import subprocess

def test_ssl_variations():
    host = "gateway.globalfishingwatch.org"
    port = 443
    print(f"=== Testing SSL/TLS handshake variations for {host} ===")

    # Test A: Windows System Curl (uses Schannel or OpenSSL)
    print("\n--- Test A: Windows curl.exe https://gateway.globalfishingwatch.org/v3/datasets ---")
    try:
        res = subprocess.run(["curl.exe", "-v", "--silent", "https://gateway.globalfishingwatch.org/v3/datasets"], capture_output=True, text=True, timeout=10)
        print(f"curl exit code: {res.returncode}")
        print(f"curl stderr snippet: {res.stderr[:400]}")
        print(f"curl stdout snippet: {res.stdout[:200]}")
    except Exception as e:
        print(f"curl test failed: {e}")

    # Test B: TLS 1.2 explicit
    print("\n--- Test B: Python ssl context with TLS 1.2 ---")
    try:
        sock = socket.create_connection((host, port), timeout=10.0)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.options |= ssl.OP_NO_TLSv1_3  # Force TLS 1.2
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        print(f"TLS 1.2 SUCCESS! Cipher: {ssl_sock.cipher()}")
        ssl_sock.close()
    except Exception as e:
        print(f"TLS 1.2 Failed: {type(e).__name__} - {e}")

    # Test C: TLS 1.3 explicit
    print("\n--- Test C: Python ssl context with TLS 1.3 ---")
    try:
        sock = socket.create_connection((host, port), timeout=10.0)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.options |= ssl.OP_NO_TLSv1_2  # Force TLS 1.3
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        print(f"TLS 1.3 SUCCESS! Cipher: {ssl_sock.cipher()}")
        ssl_sock.close()
    except Exception as e:
        print(f"TLS 1.3 Failed: {type(e).__name__} - {e}")

    # Test D: Powershell Invoke-WebRequest
    print("\n--- Test D: PowerShell Invoke-WebRequest ---")
    try:
        ps_cmd = "Invoke-WebRequest -Uri 'https://gateway.globalfishingwatch.org/v3/datasets' -UseBasicParsing"
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=10)
        print(f"PowerShell exit code: {res.returncode}")
        print(f"PowerShell stdout: {res.stdout[:200]}")
        print(f"PowerShell stderr: {res.stderr[:200]}")
    except Exception as e:
        print(f"PowerShell test failed: {e}")

if __name__ == "__main__":
    test_ssl_variations()
