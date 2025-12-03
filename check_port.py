import socket
import psutil

def check_port(port):
    print(f"Checking port {port}...")
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            print(f"Port {port} is in use by PID {conn.pid}")
            try:
                p = psutil.Process(conn.pid)
                print(f"Process Name: {p.name()}")
                print(f"Command Line: {p.cmdline()}")
            except psutil.NoSuchProcess:
                print("Process no longer exists")
            return
    print(f"Port {port} is free")

if __name__ == "__main__":
    check_port(8000)
