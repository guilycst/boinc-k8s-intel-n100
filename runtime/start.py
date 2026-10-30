"""Prepare persistent BOINC preferences and launch the selected thermal guard."""
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def prepare(data, config, memory_limit, host_memory, gpu):
    reserve = 256 * 1024**2
    if memory_limit <= reserve or host_memory <= 0:
        raise ValueError('Memory limit must exceed the 256 MiB client reserve')
    for name in ('cc_config.xml', 'global_prefs_override.xml'):
        shutil.copyfile(config / name, data / name)
    prefs = ET.parse(data / 'global_prefs_override.xml')
    percent = min(100.0, 100.0 * (memory_limit - reserve) / host_memory)
    for name in ('ram_max_used_busy_pct', 'ram_max_used_idle_pct'):
        prefs.getroot().find(name).text = str(percent)
    prefs.getroot().find('leave_apps_in_memory').text = '1'
    if gpu:
        client = ET.parse(data / 'cc_config.xml')
        options = client.getroot().find('options')
        options.find('no_gpus').text = '0'
        options.find('ncpus').text = '1'
        ET.SubElement(options, 'device_name').text = 'boinc-0'
        client.write(data / 'cc_config.xml')
        prefs.getroot().find('run_gpu_if_user_active').text = '1'
    prefs.write(data / 'global_prefs_override.xml')


def main():
    gpu = os.environ.get('BOINC_GPU_PILOT') == '1'
    if gpu and os.environ.get('POD_NAME') != 'boinc-0':
        raise SystemExit('GPU pilot requires the single StatefulSet pod boinc-0')
    os.umask(0o077)
    host_memory = next(
        int(line.split()[1]) * 1024
        for line in Path('/proc/meminfo').read_text().splitlines()
        if line.startswith('MemTotal:')
    )
    prepare(Path('/var/lib/boinc'), Path('/config'),
            int(os.environ['BOINC_MEMORY_LIMIT_BYTES']), host_memory, gpu)
    os.chdir('/var/lib/boinc')
    guard = '/gpu/guard.py' if gpu else '/cpu/guard.py'
    os.execv('/usr/bin/python3', ['python3', guard])


if __name__ == '__main__':
    main()
