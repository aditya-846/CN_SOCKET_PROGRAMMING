import json
import time

# ── Packet encode / decode ─────────────────────────────────────────────────
def create_log_packet(source_id, level, message):
    return json.dumps({
        "source":    source_id,
        "timestamp": time.time(),
        "level":     level,
        "message":   message
    }).encode("utf-8")

def parse_log_packet(data):
    return json.loads(data.decode("utf-8"))

# ── Backpressure signals ───────────────────────────────────────────────────
BP_OK   = b"OK"    # Queue is fine   — keep sending at current rate
BP_SLOW = b"SLOW"  # Queue filling   — slow your send rate
BP_STOP = b"STOP"  # Queue FULL(500) — pause sending immediately

# ── Network config ─────────────────────────────────────────────────────────
SERVER_IP   = "10.20.201.147"   # Member 1's IP — update if changed
SERVER_PORT = 9999
BUFFER_SIZE = 4096

# ── Server limits ─────────────────────────────────────────────────────────
MAX_QUEUE    = 500   # STOP backpressure triggered when queue hits this
SLOW_AT      = int(MAX_QUEUE * 0.75)   # 375 — SLOW backpressure threshold

# ── Log content ───────────────────────────────────────────────────────────
LEVELS   = ["INFO", "WARN", "ERROR"]
MESSAGES = [
    "Disk usage at 85%",
    "User login attempt",
    "Service restarted",
    "Connection timeout",
    "Memory threshold exceeded",
    "Backup completed",
]
