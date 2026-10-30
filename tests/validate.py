"""Validate the public examples and their security/resource contracts."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import yaml

root = Path(__file__).resolve().parents[1]
for path in (root / 'config').glob('*.xml'):
    ET.parse(path)

for directory in (root, root / 'examples/cpu', root / 'device-plugin'):
    result = subprocess.run(['kubectl', 'kustomize', str(directory)],
                            check=True, text=True, capture_output=True)
    objects = list(yaml.safe_load_all(result.stdout))
    assert all(o['kind'] not in ('Secret', 'SealedSecret') for o in objects)
    for obj in objects:
        if obj['kind'] == 'ConfigMap':
            for key, value in obj.get('data', {}).items():
                if key.endswith('.xml'):
                    ET.fromstring(value)
        if obj['kind'] not in ('Deployment', 'StatefulSet'):
            continue
        pod = obj['spec']['template']['spec']
        assert pod['automountServiceAccountToken'] is False
        assert pod['securityContext']['runAsUser'] == 1000
        assert pod['securityContext']['seccompProfile']['type'] == 'RuntimeDefault'
        assert not any('secret' in v or 'hostPath' in v for v in pod['volumes'])
        for container in pod.get('initContainers', []) + pod['containers']:
            security = container['securityContext']
            assert security['readOnlyRootFilesystem'] is True
            assert security['allowPrivilegeEscalation'] is False
            assert security['capabilities']['drop'] == ['ALL']
    if directory == root:
        workloads = [o for o in objects if o['kind'] in ('StatefulSet', 'Deployment')]
        assert len(workloads) == 2
        quota = next(o['spec']['hard'] for o in objects if o['kind'] == 'ResourceQuota')
        assert quota['pods'] == '2' and quota['persistentvolumeclaims'] == '2'
        assert quota['requests.storage'] == '16Gi'
        for workload in workloads:
            assert workload['spec']['replicas'] == 1
            container = workload['spec']['template']['spec']['containers'][0]
            assert container['resources']['limits']['cpu'] == '2'
            assert container['resources']['limits']['memory'] == '2Gi'
print('Public manifests render; XML, account isolation and resource contracts passed.')
