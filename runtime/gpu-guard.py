"""One Intel GPU, thermal hysteresis, and graceful BOINC shutdown."""
import ctypes
import ctypes.util
from pathlib import Path
import signal
import subprocess
import sys
import time

PAUSE_C = 85
RESUME_C = 80


def should_run(current, temperature):
    if temperature is None or temperature >= PAUSE_C:
        return False
    if temperature <= RESUME_C:
        return True
    return current


def temperature():
    readings = []
    for name in Path('/sys/class/hwmon').glob('*/name'):
        try:
            if name.read_text().strip() != 'coretemp':
                continue
            readings.extend(float(p.read_text()) / 1000 for p in name.parent.glob('temp[0-9]*_input'))
        except (OSError, ValueError):
            return None
    return max(readings) if readings and all(0 < t < 125 for t in readings) else None


def verify_gpu():
    cl = ctypes.CDLL(ctypes.util.find_library('OpenCL') or 'libOpenCL.so.1')
    cl.clGetDeviceIDs.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    cl.clGetDeviceInfo.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    count = ctypes.c_uint()
    assert cl.clGetPlatformIDs(0, None, ctypes.byref(count)) == 0, 'No OpenCL platform'
    platforms = (ctypes.c_void_p * count.value)()
    assert cl.clGetPlatformIDs(count.value, platforms, None) == 0
    devices_found = []
    for platform in platforms:
        devices_count = ctypes.c_uint()
        status = cl.clGetDeviceIDs(platform, 4, 0, None, ctypes.byref(devices_count))
        if status == -1:  # CL_DEVICE_NOT_FOUND; e.g. a CPU-only platform.
            continue
        assert status == 0, 'OpenCL GPU enumeration failed'
        devices = (ctypes.c_void_p * devices_count.value)()
        assert cl.clGetDeviceIDs(platform, 4, devices_count.value, devices, None) == 0
        for device in devices:
            vendor = ctypes.c_uint()
            assert cl.clGetDeviceInfo(device, 0x1001, ctypes.sizeof(vendor), ctypes.byref(vendor), None) == 0
            assert vendor.value == 0x8086, 'Pilot only supports Intel GPU'
            name = ctypes.create_string_buffer(512)
            assert cl.clGetDeviceInfo(device, 0x102B, len(name), name, None) == 0
            devices_found.append(name.value.decode())
    assert len(devices_found) == 1, 'Pilot requires exactly one GPU'
    print('GPU pilot device: ' + devices_found[0], flush=True)


def main():
    verify_gpu()
    stopping = False
    process = None

    def stop(signum, frame):
        nonlocal stopping
        stopping = True
        if process is not None and process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Keep scientific work behind the startup RPC retry budget and final timeout.
    process = subprocess.Popen(['/usr/bin/boinc', '--dir', '/var/lib/boinc', '--start_delay', '90'])
    running = False
    initialized = False
    deadline = time.monotonic() + 60
    try:
        while not stopping and process.poll() is None:
            value = temperature()
            desired = should_run(running, value)
            if not initialized or desired != running:
                command = ['/usr/bin/boinccmd', '--set_gpu_mode', 'auto' if desired else 'never', '0']
                try:
                    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
                    if result.returncode:
                        raise RuntimeError('GPU mode RPC failed')
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    if initialized or time.monotonic() >= deadline:
                        raise RuntimeError('Cannot enforce GPU thermal policy')
                else:
                    running = desired
                    initialized = True
                    Path('/tmp/gpu-guard.ready').touch()
                    print(f'GPU thermal policy: {"running" if running else "paused"}, package={value} C', flush=True)
            time.sleep(2)
    finally:
        Path('/tmp/gpu-guard.ready').unlink(missing_ok=True)
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=110)
    if not stopping and process.returncode:
        raise SystemExit(process.returncode)


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        assert should_run(False, 79)
        assert not should_run(True, 85)
        assert not should_run(False, 83)
        assert should_run(True, 83)
        assert not should_run(True, None)
        print('Thermal hysteresis and missing-sensor fail-closed checks passed.')
    else:
        main()
