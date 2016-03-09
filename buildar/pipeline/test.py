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
                svc = unit['name']
                test_msg = '%s unit is active' % svc
                run_result = run('systemctl is-active %s' % svc, quiet=True)
                if run_result.succeeded:
                    pass_message(test_msg)
                else:
                    fail_message(test_msg)
                    self.failed = True

    def verify_file_contents(self, remote_path, local_path):
            hash_md5 = hashlib.md5()
            hash_md5.update(open(local_path, 'r').read())
            local_md5 = hash_md5.hexdigest()

            run_result = run('md5sum %s' % remote_path, quiet=True)
            if run_result.failed:
                self.failed = True
                fail_message(test_message)

            remote_md5 = run_result.stdout.split()[0]

            return local_md5 == remote_md5

    def verify_files(self):
        """Ensure that the contents of files copied to the bastion match the contents
        of the files locally."""

        print 'Testing files...'
        for fil in self.config['files']:
            fname = fil['name']

            local_path = os.path.join(os.getcwd(), 'files', fname)
            remote_path = fil['remote_path']
            test_message = 'File contents match %s -> %s' % (local_path, remote_path)

            if self.verify_file_contents(remote_path, local_path):
                pass_message(test_message)
            else:
                self.failed = True
                fail_message(test_message)

    def verify_monitor(self):
        """Inspect the output from the bastion monitor and make sure everything
        working as it should be."""

        print 'Testing bastion state...'
        run_result = run('docker pull busybox', quiet=True)
        if run_result.failed:
            self.failed = True
            raise StandardError('Failed to pull busybox image.')

        test_cmd = 'docker run --rm -it --net container:sleeper busybox wget -qO- http://localhost:4001/health_check'
        run_result = run(test_cmd, quiet=True)
        if run_result.failed:
            self.failed = True
            raise StandardError('Failed to pull busybox image.')

        monitor_response = run_result.stdout
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
