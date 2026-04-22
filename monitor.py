"""
monitor.py — Real-time throughput and backpressure monitor
Run this on Member 3's machine (Mac) to simulate and display monitoring.

In a full integration, this would hook into the aggregator's stats dict.
Here it demonstrates the monitoring logic with a simulated log stream.
"""

import time
import threading
import collections
import random
from common import *

class ThroughputMonitor:
    def __init__(self):
        self.timestamps = collections.deque()   # Timestamp of each log event
        self.bp_events  = {"SLOW": 0, "STOP": 0}
        self.lock       = threading.Lock()
        self.total_logs = 0

    # ── Record an incoming log ────────────────────────────────────────────
    def record_log(self):
        with self.lock:
            self.timestamps.append(time.time())
            self.total_logs += 1

    # ── Record a backpressure event ───────────────────────────────────────
    def record_backpressure(self, event_type):
        with self.lock:
            if event_type in self.bp_events:
                self.bp_events[event_type] += 1
                print(
                    f"[Monitor] {'⚠️ ' if event_type == 'SLOW' else '🛑'} "
                    f"Backpressure event: {event_type} | "
                    f"Total: SLOW={self.bp_events['SLOW']} STOP={self.bp_events['STOP']}"
                )

    # ── Calculate logs/sec over last N seconds ───────────────────────────
    def throughput_last_n_seconds(self, n=5):
        cutoff = time.time() - n
        with self.lock:
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.popleft()
            return len(self.timestamps) / n

    # ── Print report every interval seconds ──────────────────────────────
    def report_loop(self, interval=5.0):
        print("[Monitor] 📊 Throughput monitor started.")
        print(f"[Monitor]    Backpressure SLOW threshold : queue ≥ {SLOW_AT} logs")
        print(f"[Monitor]    Backpressure STOP threshold : queue ≥ {MAX_QUEUE} logs\n")
        while True:
            time.sleep(interval)
            tps = self.throughput_last_n_seconds(n=interval)
            with self.lock:
                slow = self.bp_events["SLOW"]
                stop = self.bp_events["STOP"]
                total = self.total_logs
            print(f"\n{'─'*50}")
            print(f"  📊 Monitor Report")
            print(f"  Throughput    : {tps:.2f} logs/sec (last {interval:.0f}s)")
            print(f"  Total logs    : {total}")
            print(f"  BP SLOW events: {slow}")
            print(f"  BP STOP events: {stop}")
            if slow + stop > 0:
                print(f"  ⚠️  Backpressure active — producers are being throttled")
            else:
                print(f"  ✅ No backpressure — system running smoothly")
            print(f"{'─'*50}")

    def start(self):
        threading.Thread(target=self.report_loop, daemon=True).start()


# ── Standalone demo ───────────────────────────────────────────────────────
if __name__ == "__main__":
    monitor = ThroughputMonitor()
    monitor.start()

    print("[Monitor] Simulating log stream for 30 seconds...\n")
    end = time.time() + 30
    while time.time() < end:
        monitor.record_log()

        # Randomly simulate backpressure events (5% chance)
        if random.random() < 0.05:
            bp = random.choice(["SLOW", "STOP"])
            monitor.record_backpressure(bp)

        time.sleep(random.uniform(0.02, 0.1))

    print("\n[Monitor] Simulation complete.")
