#!/usr/bin/env python

import os
import sys
import pprint
import yaml
import json
import click

from buildar.pipeline.pipeline import Builder, Provisioner, Imager, Pipeline, Launcher, Tester, Publisher

@click.command()
@click.option('--region', default='us-east-1', help='Region to build in.')
@click.option('--vpc', default='vpc-31a0cc54', help='VPC to build in.')
@click.option('--cleanup/--no-cleanup', default=True, help='Run cleanup steps for pipelines.')
@click.option('--publish/--no-publish', default=False, help='Publish AMIs at the end of the build')

def build(region, vpc, cleanup, publish):
    cfg_file = file('buildar.yaml', 'r')
    config = yaml.load(cfg_file)

    vpn_password = os.getenv('BASTION_VPN_PASSWORD')
    if vpn_password == '':
        print 'You must set the BASTION_VPN_PASSWORD environment variable for the build bastion.'
        sys.exit(1)

    build_context = {
        'build_vpc': vpc,
        'build_region': region,
        'customer_id': config['customer_id'],
        'customer_email': config['customer_email'],
        'bastion_id': config['bastion_id'],
        'bastion_version': config['bastion_version'],
        'vpn_password': os.getenv('BASTION_VPN_PASSWORD'),
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

    pipeline.execute(build_context)

    if publish:
        p = Publisher()
        p.build(build_context)

    if not cleanup:
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(build_context)

if __name__ == '__main__':
    build(auto_envvar_prefix='BUILDAR')
