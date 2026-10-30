"""Pause CPU-only BOINC on Intel package heat; retain suspended processes."""
from pathlib import Path
import signal
import subprocess
import sys
import time

PAUSE_C = 85
RESUME_C = 80


def should_run(current, value):
    if value is None or value >= PAUSE_C:
        return False
    if value <= RESUME_C:
        return True
    return current


def temperature():
    values = []
    try:
        for name in Path('/sys/class/hwmon').glob('*/name'):
            if name.read_text().strip() == 'coretemp':
                values.extend(float(p.read_text()) / 1000 for p in name.parent.glob('temp[0-9]*_input'))
    except (OSError, ValueError):
        return None
    return max(values) if values and all(0 < v < 125 for v in values) else None


def main():
    stopping = False
    process = None

    def stop(signum, frame):
        nonlocal stopping
        stopping = True
        if process is not None and process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    process = subprocess.Popen(['/usr/bin/boinc', '--dir', '/var/lib/boinc', '--no_gpus', '--start_delay', '30'])
    initialized = False
    running = False
    # Fail before BOINC's 30-second application start delay expires.
    deadline = time.monotonic() + 20
    try:
        while not stopping and process.poll() is None:
            value = temperature()
            desired = should_run(running, value)
            if not initialized or desired != running:
                try:
                    result = subprocess.run(
                        ['/usr/bin/boinccmd', '--set_run_mode', 'auto' if desired else 'never', '0'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
                    if result.returncode:
                        raise RuntimeError('CPU mode RPC failed')
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    if initialized or time.monotonic() >= deadline:
                        raise RuntimeError('Cannot enforce CPU thermal policy')
                else:
                    running = desired
                    initialized = True
                    Path('/tmp/cpu-guard.ready').touch()
                    print(f'CPU thermal policy: {"running" if running else "paused"}, package={value} C', flush=True)
            time.sleep(2)
    finally:
        Path('/tmp/cpu-guard.ready').unlink(missing_ok=True)
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=110)
    if not stopping and process.returncode:
        raise SystemExit(process.returncode)


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        assert should_run(False, 79)
        assert should_run(False, 80)
        assert not should_run(True, 85)
        assert not should_run(False, 83)
        assert should_run(True, 83)
        assert not should_run(True, None)
        print('CPU thermal hysteresis and missing-sensor fail-closed checks passed.')
    else:
        main()
