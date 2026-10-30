"""Exercise real BOINC parsing and app_config overrides without a GPU/network."""
from pathlib import Path
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET


def verify(override):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        (root / 'cc_config.xml').write_text('''<cc_config><options>
<no_gpus>1</no_gpus><ncpus>1</ncpus><start_delay>3600</start_delay>
<coproc><type>pilot</type><count>1</count><peak_flops>1000000</peak_flops></coproc>
</options></cc_config>''')
        (root / 'account_127.0.0.1_1.xml').write_text('''<account>
<master_url>http://127.0.0.1:1/</master_url><authenticator>fixture</authenticator>
<project_name>fixture</project_name></account>''')
        state = ET.Element('client_state')
        project = ET.SubElement(state, 'project')
        ET.SubElement(project, 'master_url').text = 'http://127.0.0.1:1/'
        ET.SubElement(project, 'project_name').text = 'fixture'
        for name, gpu_usage in [('gpu-fractional', 0.25), ('gpu-multiple', 2), ('cpu', None)]:
            app = ET.SubElement(state, 'app')
            ET.SubElement(app, 'name').text = name
            ET.SubElement(app, 'user_friendly_name').text = name
            version = ET.SubElement(state, 'app_version')
            for key, value in [('app_name', name), ('version_num', '1'),
                               ('platform', 'x86_64-pc-linux-gnu'), ('plan_class', 'fixture'),
                               ('avg_ncpus', '0.75')]:
                ET.SubElement(version, key).text = value
            if gpu_usage is not None:
                coproc = ET.SubElement(version, 'coproc')
                ET.SubElement(coproc, 'type').text = 'pilot'
                ET.SubElement(coproc, 'count').text = str(gpu_usage)
        ET.ElementTree(state).write(root / 'client_state.xml')
        if override:
            project_dir = root / 'projects/127.0.0.1_1'
            project_dir.mkdir(parents=True)
            (project_dir / 'app_config.xml').write_text('''<app_config><app>
<name>gpu-fractional</name><gpu_versions><gpu_usage>0.125</gpu_usage>
<cpu_usage>0.1</cpu_usage></gpu_versions></app></app_config>''')
        with (root / 'log').open('w') as log:
            process = subprocess.Popen(['/usr/bin/boinc', '--dir', folder, '--no_info_fetch',
                                        '--skip_cpu_benchmarks', '--gui_rpc_port', '31599'],
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    if 'Initialization completed' in (root / 'log').read_text():
                        break
                    if process.poll() is not None:
                        raise AssertionError('Fixture client exited during initialization')
                    time.sleep(0.1)
                else:
                    raise AssertionError('Fixture client did not initialize')
            finally:
                process.terminate()
                process.wait(timeout=20)
        versions = {v.findtext('app_name'): v for v in ET.parse(root / 'client_state.xml').findall('app_version')}
        assert float(versions['gpu-fractional'].findtext('coproc/count')) == 1, 'Fractional GPU sharing escaped clamp'
        assert float(versions['gpu-multiple'].findtext('coproc/count')) == 2, 'Multi-GPU requests must not be undersized'
        assert versions['cpu'].find('coproc') is None, 'CPU task became a GPU task'
        assert float(versions['cpu'].findtext('avg_ncpus')) == 0.75, 'CPU scheduling changed'
        if override:
            assert float(versions['gpu-fractional'].findtext('avg_ncpus')) == 0.1, 'app_config fixture was not applied'


if __name__ == '__main__':
    verify(False)
    verify(True)
    print('Whole-device GPU reservation verified before and after app_config overrides; CPU task unchanged.')
