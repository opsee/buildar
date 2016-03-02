from os import path
import os, sys, yaml

from fabric.api import run, execute, put, env, sudo

from buildar.pipeline.step import Step

class Provisioner(Step):
    def __init__(self, config):
        cfg = yaml.load(config)
        self._units = cfg['units']
        self._files = cfg['files']

        env.user = 'core'
        env.connection_attempts = 10
        env.timeout = 30

    def _install_units(self):
        # We put all of the units at once, so that dependencies don't have to be
        # considered when writing buildar.yaml
        for unit in self._units:
            unit_name = unit['name']
            unit_path = path.join(os.getcwd(), 'units', unit_name)
            remote_path = '/etc/systemd/system/%s' % unit_name

            result = put(local_path=unit_path,
                         remote_path=remote_path,
                         use_sudo=True)

            if result.failed:
                raise Exception('Unable to copy unit to remote host: %s' % unit_name)

        for unit in self._units:
            unit_action = unit['action']
            unit_name = unit['name']

            result = sudo('systemctl %s %s' % (unit_action, unit_name), stderr=sys.stdout)
            if result.failed:
                raise Exception('Unable to %s systemd unit: %s' % (unit_action, unit_name))

    def _copy_files(self):
        for f in self._files:
            local_path = path.join(os.getcwd(), 'files', f['name'])
            remote_path = f['remote_path']
            result = put(local_path=local_path,
                         remote_path=remote_path,
                         use_sudo=True)

            if result.failed:
                raise Exception('Unable to copy file to remote host: %s' % f['name'])

            if f.has_key('user'):
                result = sudo('chown %s %s' % (f['user'], remote_path), stderr=sys.stdout)
                if result.failed:
                    raise Exception('Unable to chown file: %s' % f['name'])

            if f.has_key('group'):
                result = sudo('chgrp %s %s' % (f['user'], remote_path), stderr=sys.stdout)
                if result.failed:
                    raise Exception('Unable to copy file to remote host: %s' % f['name'])

            if f.has_key('mode'):
                result = sudo('chmod %o %s' % (f['mode'], remote_path), stderr=sys.stdout)
                if result.failed:
                    raise Exception('Unable to chmod file: %s' % f['name'])

    def _shutdown(self):
        sudo('shutdown -h now', stderr=sys.stdout, quiet=True)

    def provision_bastion(self):
        self._install_units()
        self._copy_files()
        self._shutdown()

    def build(self, build_context):
        env.key = build_context['ssh_key']
        execute(self.provision_bastion, hosts=[build_context['public_ip']])
        return build_context

    def cleanup(self, build_context):
        pass
