#!/usr/bin/env python

import click

from buildar.pipeline.pipeline import Builder, Provisioner, Imager, Pipeline, Launcher, Tester

@click.command()
@click.option('--region', default='us-east-1', help='Region to build in.')
@click.option('--vpc', default='vpc-31a0cc54', help='VPC to build in.')
@click.option('--cleanup/--no-cleanup', default=True, help='Run cleanup steps for pipelines')

def build(region, vpc, cleanup):
    build_context = {
        'build_vpc': vpc,
        'build_region': region,
    }

    config = file('buildar.yaml', 'r')
    build_pipeline = Pipeline(cleanup=cleanup)
    build_pipeline.add_step(Builder())
    build_pipeline.add_step(Provisioner(config))
    build_pipeline.add_step(Imager())

    test_pipeline = Pipeline(cleanup=cleanup)
    test_pipeline.add_step(Launcher())
    test_pipeline.add_step(Tester())

    pipeline = Pipeline(cleanup=cleanup)
    pipeline.add_step(build_pipeline)
    pipeline.add_step(test_pipeline)

    pipeline.execute(build_context)

if __name__ == '__main__':
    build(auto_envvar_prefix='BUILDAR')
