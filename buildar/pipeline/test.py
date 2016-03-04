"""Test will test an instance to ensure that everything is running as it should
be. It shares configuration with the provisioner."""

import sys
import time
import os
import json
import hashlib
import StringIO

from click import style, echo
from fabric.api import env, execute, run
from buildar.pipeline.step import Step

def fail_message(msg):
    """Helper to print a failing message."""

    echo(style('%s: FAIL' % msg, fg='red'))

def pass_message(msg):
    """Helper to print a passing test message."""

    echo(style('%s: PASS' % msg, fg='green'))

class Tester(Step):
    """Use Fabric and envassert to ensure that services are running, files
    are in place with the correct ownership and permissions, etc."""

    def __init__(self, config, **kwargs):
        super(Tester, self).__init__(**kwargs)
        self.config = config
        self.failed = False

    def verify_units(self):
        """Inspect the systemd units running on the bastion test instance."""

        print 'Testing bastion units...'
        for unit in self.config['units']:
            if unit['name'].endswith('.service'):
                out = StringIO.StringIO()
                svc = unit['name']
                test_msg = '%s unit is active' % svc
                run_result = run('systemctl is-active %s' % svc, stdout=out, stderr=out)
                if run_result.succeeded:
                    pass_message(test_msg)
                else:
                    fail_message(test_msg)
                    print 'Output from command:'
                    print out.getvalue()
                    self.failed = True
                out.close()

    def verify_files(self):
        """Ensure that the contents of files copied to the bastion match the contents
        of the files locally."""

        print 'Testing files...'
        hash_md5 = hashlib.md5()
        for fil in self.config['files']:
            fname = fil['name']

            local_path = os.path.join(os.getcwd(), fname)
            remote_path = fil['remote_path']
            test_message = 'File contents match %s -> %s' % (local_path, remote_path)

            with open(local_path, "rb") as fio:
                for chunk in iter(lambda: fio.read(4096), b""):
                    hash_md5.update(chunk)
            local_md5 = hash_md5.hexdigest()

            out = StringIO.StringIO()
            run_result = run('md5sum %s' % remote_path, stdout=out)
            if run_result.failed:
                self.failed = True
                fail_message(test_message)
            remote_md5 = out.getvalue()

            if local_md5 == remote_md5:
                pass_message(test_message)
            else:
                fail_message(test_message)
                self.failed = True

    def verify_monitor(self):
        """Inspect the output from the bastion monitor and make sure everything
        working as it should be."""

        print 'Testing bastion state...'
        run_result = run('docker pull busybox', quiet=True)
        if run_result.failed:
            self.failed = True
            raise StandardError('Failed to pull busybox image.')

        out = StringIO.StringIO()
        test_cmd = 'docker run --rm -it --net container:sleeper busybox wget -qO- http://localhost:4001/health_check'
        run_result = run(test_cmd, stdout=out, stderr=sys.stdout)
        if run_result.failed:
            self.failed = True
            raise StandardError('Failed to pull busybox image.')

        monitor_response = out.getvalue()
        monitor = json.loads(monitor_response)
        for svc, state in monitor.iteritems():
            test_msg = '%s is alive' % svc
            if state['ok']:
                pass_message(test_msg)
            else:
                self.failed = True
                fail_message(test_msg)

    def build(self, build_context):
        """Run tests on a newly launched bastion test instance."""

        # TODO(greg): There has to be a better way to do this... Maybe run all
        # of the tests and give them a period of time to be consistent? This
        # test is pretty simple and lame.

        print 'Sleeping for 120 seconds to allow bastion to finish initialization...'
        time.sleep(120)

        env.user = 'core'
        env.connection_attempts = 10
        env.timeout = 30
        env.key = build_context['ssh_key']
        env.hosts = build_context['launch_public_ip']
        execute(self.verify_units)
        execute(self.verify_files)
        execute(self.verify_monitor)

        if self.failed:
            raise StandardError('Bastion failed verification step.')

        return build_context

    def cleanup(self, build_context):
        if self.do_cleanup:
            pass
