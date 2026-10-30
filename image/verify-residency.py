"""Exercise GPU scheduler preemption with a sleeping, hardware-free fixture."""
from pathlib import Path
import subprocess,tempfile,time,shutil,xml.etree.ElementTree as E,re,os,signal
with tempfile.TemporaryDirectory() as d:
 p=Path(d);url='http://127.0.0.1:1/'
 (p/'cc_config.xml').write_text('<cc_config><options><no_gpus>0</no_gpus><ncpus>1</ncpus><coproc><type>pilot</type><count>1</count><peak_flops>1000000</peak_flops></coproc></options></cc_config>')
 (p/'global_prefs_override.xml').write_text('<global_preferences><max_ncpus_pct>100</max_ncpus_pct><cpu_usage_limit>100</cpu_usage_limit><run_if_user_active>1</run_if_user_active><run_gpu_if_user_active>1</run_gpu_if_user_active><suspend_cpu_usage>0</suspend_cpu_usage><leave_apps_in_memory>1</leave_apps_in_memory><run_on_batteries>1</run_on_batteries></global_preferences>')
 (p/'account_127.0.0.1_1.xml').write_text(f'<account><master_url>{url}</master_url><authenticator>fixture</authenticator><project_name>fixture</project_name></account>')
 project=p/'projects/127.0.0.1_1';project.mkdir(parents=True);(project/'pilot-worker').write_text('#!/usr/bin/python3\nimport time\nwhile True: time.sleep(1)\n');(project/'pilot-worker').chmod(0o755)
 size=(project/'pilot-worker').stat().st_size
 (p/'client_state.xml').write_text(f'''<client_state>
 <project><master_url>{url}</master_url><project_name>fixture</project_name></project>
 <app><name>pilot</name><user_friendly_name>fixture</user_friendly_name></app>
 <file_info><name>pilot-worker</name><nbytes>{size}</nbytes><status>1</status><executable/></file_info>
 <app_version><app_name>pilot</app_name><version_num>1</version_num><platform>x86_64-pc-linux-gnu</platform><plan_class>fixture</plan_class><avg_ncpus>0.1</avg_ncpus><cmdline>600</cmdline><coproc><type>pilot</type><count>1</count></coproc><file_ref><file_name>pilot-worker</file_name><main_program/></file_ref></app_version>
 <workunit><name>fixture</name><app_name>pilot</app_name><rsc_fpops_est>100000000000</rsc_fpops_est><rsc_fpops_bound>1000000000000000</rsc_fpops_bound><rsc_memory_bound>1000000</rsc_memory_bound><rsc_disk_bound>1000000</rsc_disk_bound></workunit>
 <result><name>fixture</name><wu_name>fixture</wu_name><platform>x86_64-pc-linux-gnu</platform><plan_class>fixture</plan_class><version_num>1</version_num><state>2</state><report_deadline>{time.time()+86400}</report_deadline></result>
 </client_state>''')
 f=(p/'log').open('w');proc=subprocess.Popen(['/usr/bin/boinc','--dir',d,'--no_info_fetch','--skip_cpu_benchmarks','--unsigned_apps_ok','--gui_rpc_port','31599'],stdout=f,stderr=subprocess.STDOUT)
 def rpc(*cmd):return subprocess.check_output(['/usr/bin/boinccmd','--host','127.0.0.1:31599']+list(cmd),cwd=d,text=True,stderr=subprocess.STDOUT)
 pid = None
 def wait_state(expected):
  deadline=time.monotonic()+15
  while time.monotonic()<deadline:
   try: output=rpc('--get_tasks')
   except subprocess.CalledProcessError:
    time.sleep(0.1);continue
   if 'active_task_state: '+expected in output:
    return output
   if 'state: compute error' in output: raise AssertionError('Fixture failed to start')
   time.sleep(0.2)
  raise AssertionError('GPU fixture did not reach '+expected)
 try:
  initial=wait_state('EXECUTING');pid=int(re.search(r'PID: (\d+)',initial)[1]);assert pid>0
  rpc('--set_gpu_mode','never','0')
  paused=wait_state('SUSPENDED');assert int(re.search(r'PID: (\d+)',paused)[1])==pid
  time.sleep(3)
  assert 'active_task_state: SUSPENDED' in rpc('--get_tasks'), 'Suspended GPU was removed by scheduling cleanup'
  rpc('--set_gpu_mode','always','0')
  resumed=wait_state('EXECUTING');assert int(re.search(r'PID: (\d+)',resumed)[1])==pid
  print('GPU task retained same PID across pause, suspended-task cleanup and resume.')

 finally:
  if pid:
   try: os.kill(pid, signal.SIGTERM)
   except ProcessLookupError: pass
  proc.terminate()
  try:proc.wait(timeout=25)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
  f.close()
