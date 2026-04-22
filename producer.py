import socket
import ssl
import time
import random
import sys
from common import *

class Producer:
    def __init__(self, source_id):
        self.source_id     = source_id
        self.send_interval = 0.1   # seconds between sends (adjustable)

        # ── Client-side backpressure stats ────────────────────────────────
        self.bp_stats = {
            "ok_count":   0,
            "slow_count": 0,
            "stop_count": 0,
        }

        # ── SSL Context (Client) ──────────────────────────────────────────
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_cert_chain("client.crt", "client.key")  # Client's own certificate
        ctx.load_verify_locations("ca.crt")               # Trust only our CA
        ctx.check_hostname = False                         # Self-signed cert, no hostname check

        # ── Connect to aggregator with SSL ────────────────────────────────
        raw_sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = ctx.wrap_socket(raw_sock, server_hostname=SERVER_IP)
        self.sock.settimeout(5.0)

        print(f"[{source_id}] Connecting to {SERVER_IP}:{SERVER_PORT}...")
        self.sock.connect((SERVER_IP, SERVER_PORT))

        # Print server certificate info to confirm mutual auth
        cert    = self.sock.getpeercert()
        subject = dict(x[0] for x in cert.get("subject", []))
        cn      = subject.get("commonName", "Unknown")
        print(f"[{source_id}] ✅ SSL Handshake complete!")
        print(f"[{source_id}]    Server cert CN  : {cn}")
        print(f"[{source_id}]    Verified by CA  : ca.crt")
        print(f"[{source_id}]    Cipher in use   : {self.sock.cipher()[0]}\n")

    # ── Send one log and handle the backpressure reply ────────────────────
    def send_log(self, level, message):
        packet = create_log_packet(self.source_id, level, message)
        self.sock.send(packet)

        try:
            signal = self.sock.recv(64)
            self.handle_backpressure(signal)
        except socket.timeout:
            pass  # No reply received, continue

    # ── React to server's backpressure signal ─────────────────────────────
    def handle_backpressure(self, signal):
        if signal == BP_SLOW:
            # ── Client Backpressure: SLOW ──────────────────────────────
            self.bp_stats["slow_count"] += 1
            old_interval = self.send_interval
            self.send_interval = min(self.send_interval * 1.5, 2.0)
            print(
                f"[{self.source_id}] [BP] ⚠️  SLOW received | "
                f"Interval: {old_interval:.2f}s → {self.send_interval:.2f}s | "
                f"Total SLOWs: {self.bp_stats['slow_count']}"
            )

        elif signal == BP_STOP:
            # ── Client Backpressure: STOP ──────────────────────────────
            # Server queue is FULL (500/500) — this log was DROPPED
            self.bp_stats["stop_count"] += 1
            print(
                f"[{self.source_id}] [BP] 🛑 STOP received | "
                f"⚠️  LOG DROPPED by server (queue full at {MAX_QUEUE}) | "
                f"Total dropped: {self.bp_stats['stop_count']}"
            )
            time.sleep(2)   # Brief pause then keep sending to show overflow

        elif signal == BP_OK:
            # ── Client Backpressure: OK — gradually speed back up ──────
            self.bp_stats["ok_count"] += 1
            self.send_interval = max(self.send_interval * 0.9, 0.05)

    # ── Main send loop ────────────────────────────────────────────────────
    def run(self, num_logs=700):  # 700 > MAX_QUEUE(500) — forces overflow scenario
        print(f"[{self.source_id}] Starting to send {num_logs} logs (MAX_QUEUE={MAX_QUEUE} — overflow expected!)\n")
        for i in range(num_logs):
            level   = random.choice(LEVELS)
            message = random.choice(MESSAGES) + f" (log #{i})"
            self.send_log(level, message)
            if i < 5 or i % 50 == 0:   # Print first 5 and every 50th to avoid spam
                print(f"[{self.source_id}] Sent [{level:<5}] {message}")
            time.sleep(self.send_interval)

        # ── Print client-side backpressure summary ─────────────────────
        print(f"\n{'='*50}")
        print(f"[{self.source_id}] ✅ Done. Backpressure Summary (Client Side):")
        print(f"  OK signals   received : {self.bp_stats['ok_count']}")
        print(f"  SLOW signals received : {self.bp_stats['slow_count']}")
        print(f"  STOP signals received : {self.bp_stats['stop_count']}")
        print(f"{'='*50}\n")
        self.sock.close()

if __name__ == "__main__":
    source_id = sys.argv[1] if len(sys.argv) > 1 else "machine-1"
    num_logs  = int(sys.argv[2]) if len(sys.argv) > 2 else 700
    Producer(source_id).run(num_logs)
