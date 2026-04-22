import socket
import ssl
import threading
import heapq
import time
from common import *

class Aggregator:
    def __init__(self):
        # ── SSL Context (Server) ───────────────────────────────────────────
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain("server.crt", "server.key")  # Server's certificate
        self.ctx.load_verify_locations("ca.crt")              # Trust only our CA
        self.ctx.verify_mode = ssl.CERT_REQUIRED              # REQUIRE client certificate

        # ── TCP Socket ────────────────────────────────────────────────────
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_sock.bind((SERVER_IP, SERVER_PORT))
        raw_sock.listen(10)
        self.server_sock = raw_sock

        # ── Shared log heap ───────────────────────────────────────────────
        self.log_heap  = []
        self.heap_lock = threading.Lock()

        # ── Server-side backpressure stats ────────────────────────────────
        self.stats = {
            "received": 0,
            "dropped":  0,
            "bp_slow":  0,   # times server sent SLOW
            "bp_stop":  0,   # times server sent STOP
        }

    # ── Decide which backpressure signal to send ──────────────────────────
    def get_bp_signal(self):
        size = len(self.log_heap)
        if size >= MAX_QUEUE:   # 500 → STOP
            return BP_STOP
        elif size >= SLOW_AT:   # 375 → SLOW
            return BP_SLOW
        return BP_OK

    # ── Handle one connected client in its own thread ─────────────────────
    def handle_client(self, ssl_conn, addr):
        # Print the client's SSL certificate details
        cert = ssl_conn.getpeercert()
        subject = dict(x[0] for x in cert.get("subject", []))
        cn = subject.get("commonName", "Unknown")
        print(f"\n[Server Auth] ✅ Client connected: {addr}")
        print(f"[Server Auth]    Certificate CN : {cn}")
        print(f"[Server Auth]    Verified by CA : ca.crt\n")

        try:
            while True:
                data = ssl_conn.recv(BUFFER_SIZE)
                if not data:
                    break

                log    = parse_log_packet(data)
                signal = self.get_bp_signal()

                with self.heap_lock:
                    queue_size = len(self.log_heap)

                    if signal == BP_STOP:
                        # ── Queue FULL at 500 — drop this log ─────────
                        self.stats["dropped"]  += 1
                        self.stats["bp_stop"]  += 1
                        print(
                            f"[Server BP] 🛑  QUEUE FULL ({MAX_QUEUE}/{MAX_QUEUE}) | "
                            f"LOG DROPPED from {log['source']} | "
                            f"Total dropped: {self.stats['dropped']}"
                        )
                        ssl_conn.send(BP_STOP)
                        continue

                    if signal == BP_SLOW:
                        # ── Server Backpressure: SLOW ──────────────────
                        self.stats["bp_slow"] += 1
                        print(
                            f"[Server BP] ⚠️   SLOW → {log['source']} | "
                            f"Queue: {queue_size}/{MAX_QUEUE} ({queue_size*100//MAX_QUEUE}% full) | "
                            f"Total SLOWs sent: {self.stats['bp_slow']}"
                        )

                    heapq.heappush(self.log_heap, (log["timestamp"], log))
                    self.stats["received"] += 1
                    ssl_conn.send(signal)

        except (ConnectionResetError, ssl.SSLError, OSError) as e:
            print(f"[Server] Client {addr} disconnected: {e}")
        finally:
            ssl_conn.close()
            print(f"[Server] Connection closed: {addr}")

    # ── Accept incoming SSL connections ───────────────────────────────────
    def accept_loop(self):
        print(f"[Server] 🔒 SSL Aggregator listening on {SERVER_IP}:{SERVER_PORT}")
        print(f"[Server]    Backpressure: SLOW at {SLOW_AT} logs, STOP at {MAX_QUEUE} logs\n")
        while True:
            try:
                raw_conn, addr = self.server_sock.accept()
                try:
                    ssl_conn = self.ctx.wrap_socket(raw_conn, server_side=True)
                except ssl.SSLError as e:
                    print(f"[Server Auth] ❌ SSL handshake failed from {addr}: {e}")
                    raw_conn.close()
                    continue
                threading.Thread(
                    target=self.handle_client,
                    args=(ssl_conn, addr),
                    daemon=True
                ).start()
            except Exception as e:
                print(f"[Server] Accept error: {e}")

    # ── Flush heap periodically ───────────────────────────────────────────
    def flush_loop(self, interval=2.0):
        while True:
            time.sleep(interval)
            with self.heap_lock:
                if not self.log_heap:
                    continue
                print("\n" + "─" * 55)
                print("  Flushing Time-Ordered Logs")
                print("─" * 55)
                while self.log_heap:
                    ts, log = heapq.heappop(self.log_heap)
                    print(
                        f"  [{log['level']:<5}] {log['source']:<12} "
                        f"@ {time.strftime('%H:%M:%S', time.localtime(ts))} "
                        f"→ {log['message']}"
                    )
                print("─" * 55)
                print(
                    f"  Stats | received={self.stats['received']}  "
                    f"dropped={self.stats['dropped']}  "
                    f"SLOW_sent={self.stats['bp_slow']}  "
                    f"STOP_sent={self.stats['bp_stop']}"
                )

    # ── Start everything ──────────────────────────────────────────────────
    def start(self):
        threading.Thread(target=self.accept_loop, daemon=True).start()
        threading.Thread(target=self.flush_loop,  daemon=True).start()
        print("[Server] Started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Server] Final Stats:")
            print(f"  Received : {self.stats['received']}")
            print(f"  Dropped  : {self.stats['dropped']}")
            print(f"  SLOW sent: {self.stats['bp_slow']}")
            print(f"  STOP sent: {self.stats['bp_stop']}")
            print("[Server] Shutting down.")

if __name__ == "__main__":
    Aggregator().start()
