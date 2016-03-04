"""Provision is the privisioning step of the bastion build process.

At this point, a build instance has been launched, and we must deploy
Opsee bastion software to the instance prior to AMI creation."""

import os
from os import path
import sys
import StringIO

import yaml
from fabric.api import run, execute, put, env, sudo

from buildar.pipeline.step import Step

class Provisioner(Step):
    """Provisioner will provision an EC2 instance."""

    def __init__(self, config):
        super
        cfg = yaml.load(config)
        self._units = cfg.get('units', [])
        self._files = cfg.get('files', [])
        self._images = cfg.get('images', [])

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

            put_result = put(local_path=unit_path,
                             remote_path=remote_path,
                             use_sudo=True)

            if put_result.failed:
                raise Exception('Unable to copy unit to remote host: %s' % unit_name)

        for unit in self._units:
            unit_action = unit['action']
            unit_name = unit['name']

            sudo_result = sudo('systemctl %s %s' % (unit_action, unit_name), stderr=sys.stdout)
            if sudo_result.failed:
                raise Exception('Unable to %s systemd unit: %s' % (unit_action, unit_name))

    def _pull_images(self):
        for image in self._images:
            print 'Pulling image %s' % image
            out = StringIO.StringIO()
            result = run('docker pull %s' % image, timeout=240, stdout=out, stderr=out)
            if result.failed:
                print out.getvalue()
                out.close()
                raise Exception('Failed to pull %s' % image)

            # This just seems easier than some ridiculous try catch raise finally close business.
            out.close()

    def _copy_files(self):
        for fil in self._files:
            local_path = path.join(os.getcwd(), 'files', fil['name'])
            remote_path = fil['remote_path']
            put_result = put(local_path=local_path,
                             remote_path=remote_path,
                             use_sudo=True)

            if put_result.failed:
                raise Exception('Unable to copy file to remote host: %s' % fil['name'])

            if 'user' in fil:
                sudo_result = sudo('chown %s %s' % (fil['user'], remote_path), stderr=sys.stdout)
                if sudo_result.failed:
                    raise Exception('Unable to chown file: %s' % fil['name'])

            if 'group' in fil:
                sudo_result = sudo('chgrp %s %s' % (fil['user'], remote_path), stderr=sys.stdout)
                if sudo_result.failed:
                    raise Exception('Unable to copy file to remote host: %s' % fil['name'])

            if 'mode' in fil:
                sudo_result = sudo('chmod %o %s' % (fil['mode'], remote_path), stderr=sys.stdout)
                if sudo_result.failed:
                    raise Exception('Unable to chmod file: %s' % fil['name'])

    def provision_bastion(self):
        """This is the Fabric task to be run."""

        self._install_units()
        # TODO(greg): Right now there is a dependency on the docker config being copied
        # over before we can pull images. That's kind of shitty. We should figure out a
        # way to do this without having that dependency. Perhaps, pull images locally,
        # then export them to a tar, scp over, and import?
        self._copy_files()
        self._pull_images()
        sudo('shutdown -h now', stderr=sys.stdout, quiet=True)

    def build(self, build_context):
        """execute the fabric task"""

        env.key = build_context['ssh_key']
        execute(self.provision_bastion, hosts=[build_context['public_ip']])
        return build_context

    def cleanup(self, build_context):
        # TODO(greg): Implement cleanup here.
        if self.do_cleanup:
            pass
