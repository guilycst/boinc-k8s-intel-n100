"""Keep BOINC application startup behind successful thermal-policy setup."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class ThermalStartupTest(unittest.TestCase):
    def test_initial_rpc_failure_stops_before_applications_start(self):
        for guard_name in ('cpu-guard', 'gpu-guard'):
            for failure in ('nonzero', 'timeout'):
                with self.subTest(guard=guard_name, failure=failure):
                    source = Path(__file__).with_name(guard_name + '.py')
                    spec = importlib.util.spec_from_file_location(guard_name, source)
                    guard = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(guard)
                    clock = SimpleNamespace(now=0.0)
                    process = Mock(returncode=None)
                    process.poll.side_effect = lambda: process.returncode
                    stopped = []
                    launched = []

                    def terminate():
                        stopped.append(clock.now)
                        process.returncode = 0

                    def sleep(seconds):
                        clock.now += seconds

                    def launch(command):
                        launched.append(float(command[command.index('--start_delay') + 1]))
                        return process

                    def rpc(command, **kwargs):
                        self.assertEqual(command[-2:], ['never', '0'])
                        if failure == 'timeout':
                            clock.now += kwargs['timeout']
                            raise guard.subprocess.TimeoutExpired(command, kwargs['timeout'])
                        return SimpleNamespace(returncode=1)

                    process.terminate.side_effect = terminate
                    with (
                        patch.object(guard, 'verify_gpu', create=True),
                        patch.object(guard, 'temperature', return_value=None),
                        patch.object(guard, 'Path'),
                        patch.object(guard.signal, 'signal'),
                        patch.object(guard.time, 'monotonic', side_effect=lambda: clock.now),
                        patch.object(guard.time, 'sleep', side_effect=sleep),
                        patch.object(guard.subprocess, 'Popen', side_effect=launch),
                        patch.object(guard.subprocess, 'run', side_effect=rpc),
                    ):
                        with self.assertRaisesRegex(RuntimeError, 'Cannot enforce'):
                            guard.main()
                    self.assertEqual(len(stopped), 1)
                    self.assertLess(stopped[0], launched[0],
                                    'BOINC could start work before the supervisor stops it')


if __name__ == '__main__':
    unittest.main()
