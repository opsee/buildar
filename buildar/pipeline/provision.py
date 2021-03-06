"""Provision is the privisioning step of the bastion build process.

At this point, a build instance has been launched, and we must deploy
Opsee bastion software to the instance prior to AMI creation."""

import os
from os import path
import sys
import StringIO

from jinja2 import Template
from fabric.api import run, execute, put, env, sudo
from fabric.network import disconnect_all

from buildar.pipeline.step import Step

class Provisioner(Step):
    """Provisioner will provision an EC2 instance."""

    def __init__(self, config, **kwargs):
        super(Provisioner, self).__init__(**kwargs)
        self._units = config.get('units', [])
        self._files = config.get('files', [])
        self._images = set()

    def _install_units(self):
        # We put all of the units at once, so that dependencies don't have to be
        # considered when writing buildar.yaml
        for unit in self._units:
            unit_name = unit['name']
            unit_path = path.join(os.getcwd(), 'units', unit_name)
            remote_path = '/etc/systemd/system/%s' % unit_name

            if 'image' in unit:
                template = Template(open(unit_path, 'r').read())
                rendered_unit = StringIO.StringIO()
                # We'll throw an exception if version is missing. Fucking
                # keep it that way. Strictly version every single unit that
                # needs it.
                rendered_unit.write(template.render(image=unit['image'], version=unit['version']))
                image = '%s:%s' % (unit['image'], unit['version'])
                self._images.add(image)
                put_result = put(local_path=rendered_unit,
                                 remote_path=remote_path,
                                 use_sudo=True,
                                 mirror_local_mode=True)
                rendered_unit.close()
            else:
                put_result = put(local_path=unit_path,
                                 remote_path=remote_path,
                                 use_sudo=True,
                                 mirror_local_mode=True)


            if put_result.failed:
                raise Exception('Unable to copy unit to remote host: %s' % unit_name)

        for unit in self._units:
            out = StringIO.StringIO()
            unit_action = unit['action']
            unit_name = unit['name']

            sudo_result = sudo('systemctl %s %s' % (unit_action, unit_name), stdout=out, stderr=out)
            if sudo_result.failed:
                print out.getvalue()
                out.close()
                raise Exception('Unable to %s systemd unit: %s' % (unit_action, unit_name))
            out.close()

    def _pull_images(self):
        for image in self._images:
            out = StringIO.StringIO()
            result = run('docker pull %s' % image, timeout=240, stdout=out, stderr=out)
            if result.failed:
                print out.getvalue()
                out.close()
                raise Exception('Failed to pull %s' % image)

            # This just seems easier than some ridiculous try catch raise finally close business.
            out.close()

    def _copy_files(self):
        sudo('mkdir /etc/systemd/system/docker.service.d', quiet=True)

        for fil in self._files:
            local_path = path.join(os.getcwd(), 'files', fil['name'])
            remote_path = fil['remote_path']
            put_result = put(local_path=local_path,
                             remote_path=remote_path,
                             use_sudo=True,
                             mirror_local_mode=True)

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

        print 'Shutting down build instance...'
        sudo('shutdown -h now', stderr=sys.stdout, quiet=True)

    def build(self, build_context):
        """execute the fabric task"""

        env.user = 'core'
        env.connection_attempts = 30
        env.timeout = 30
        env.key = build_context['ssh_key']
        env.warn_only = True
        env.use_exceptions_for['network'] = False
        env.skip_bad_hosts = True
        execute(self.provision_bastion, hosts=[build_context['public_ip']])
        disconnect_all()
        return build_context

    def cleanup(self, build_context):
        """Provisioner has no cleanup, because what would you do? Delete things before you
        terminate the instance? IDK. Maybe this makes sense later."""

        if self.do_cleanup:
            pass
        
        return build_context
