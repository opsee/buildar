#!/usr/bin/env python

import os
import sys
import pprint
import yaml
import json
import click

from buildar.pipeline.pipeline import Builder, Provisioner, Imager, Pipeline, Launcher, Tester, Publisher

@click.command()
@click.option('--region', default='us-east-1', help='Region to build in. (BUILDAR_REGION)')
@click.option('--vpc', default='vpc-31a0cc54', help='VPC to build in. (BUILDAR_VPC)')
@click.option('--cleanup/--no-cleanup', default=True, help='Run cleanup steps for pipelines.')
@click.option('--publish/--no-publish', default=False, help='Publish AMIs at the end of the build')
@click.option('--customer-id', help='Customer ID (BUILDAR_CUSTOMER_ID)')
@click.option('--customer-email', help='Customer e-mail (BUILDAR_CUSTOMER_EMAIL)')
@click.option('--bastion-id', help='Bastion ID (BUILDAR_BASTION_ID)')
@click.option('--bastion-version', help='Bastion version (BUILDAR_BASTION_VERSION)')
@click.option('--vpn-password', help='VPN password (BUILDAR_VPN_PASSWORD)')
def build(region, vpc, cleanup, publish, customer_id, customer_email, bastion_id, bastion_version, vpn_password):
    cfg_file = file('buildar.yaml', 'r')
    config = yaml.load(cfg_file)

    vpn_password = os.getenv('BASTION_VPN_PASSWORD')
    if vpn_password == '':
        print 'You must set the BASTION_VPN_PASSWORD environment variable for the build bastion.'
        sys.exit(1)

    build_context = {
        'build_vpc': vpc,
        'build_region': region,
        'customer_id': customer_id,
        'customer_email': customer_email,
        'bastion_id': bastion_id,
        'bastion_version': bastion_version,
        'vpn_password': vpn_password,
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

    pipeline.execute(build_context)

    if not cleanup:
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(build_context)

if __name__ == '__main__':
    build(auto_envvar_prefix='BUILDAR')
