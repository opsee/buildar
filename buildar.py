#!/usr/bin/env python

import os
import sys
import pprint
import yaml
import json
import click

from buildar.pipeline.pipeline import Builder, Provisioner, Imager, Pipeline, Launcher, Tester, Publisher, Tagger

@click.command()
@click.option('--region', default='us-east-1', help='Region to build in. (BUILDAR_REGION)')
@click.option('--vpc', default='vpc-31a0cc54', help='VPC to build in. (BUILDAR_VPC)')
@click.option('--cleanup/--no-cleanup', default=True, help='Run cleanup steps for pipelines.')
@click.option('--publish/--no-publish', default=False, help='Publish AMIs at the end of the build')
@click.option('--customer-id', help='Customer ID (BUILDAR_CUSTOMER_ID)')
@click.option('--customer-email', help='Customer e-mail (BUILDAR_CUSTOMER_EMAIL)')
@click.option('--bastion-id', help='Bastion ID (BUILDAR_BASTION_ID)')
@click.option('--vpn-password', help='VPN password (BUILDAR_VPN_PASSWORD)')
@click.option('--coreos-ami', default='latest', help='Build with specific coreos AMI (BUILDAR_COREOS_AMI)')
def build(region, vpc, cleanup, publish, customer_id, customer_email, bastion_id, vpn_password, coreos_ami):
    cfg_file = file('buildar.yaml', 'r')
    config = yaml.load(cfg_file)
    bastion_version = config['bastion_version']

    release_tag = 'stable' if publish else 'beta'
    build_context = {
        'build_vpc': vpc,
        'build_region': region,
        'customer_id': customer_id,
        'customer_email': customer_email,
        'bastion_id': bastion_id,
        'bastion_version': bastion_version,
        'vpn_password': vpn_password,
        'coreos_ami': coreos_ami,
        'release_tag': release_tag,
    }

    build_pipeline = Pipeline(cleanup=cleanup)
    build_pipeline.add_step(Builder())
    build_pipeline.add_step(Provisioner(config))
    build_pipeline.add_step(Imager())

    test_pipeline = Pipeline(cleanup=cleanup)
    test_pipeline.add_step(Launcher())
    test_pipeline.add_step(Tester(config))

    pipeline = Pipeline(cleanup=cleanup)
    pipeline.add_step(build_pipeline)
    pipeline.add_step(test_pipeline)

    if publish:
        pipeline.add_step(Publisher())
        pipeline.add_step(Tagger())

    pipeline.execute(build_context)

    if not cleanup:
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(build_context)

        print 'ssh -i %s core@%s' % (build_context['key_name'] + '.pem', build_context['launch_public_ip'])

if __name__ == '__main__':
    build(auto_envvar_prefix='BUILDAR')
