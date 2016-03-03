#!/usr/bin/env python

import boto3, sys, time, requests, json

from buildar.pipeline.pipeline import Builder, Provisioner, Imager, Pipeline, Launcher

build_region = 'us-east-1'
build_vpc = 'vpc-31a0cc54'
build_context = {
    'build_vpc': build_vpc,
    'build_region': build_region,
}


builder = Builder()
config = file('buildar.yaml', 'r')
provisioner = Provisioner(config)
imager = Imager()

build_pipeline = Pipeline()
build_pipeline.add_step(builder)
build_pipeline.add_step(provisioner)
build_pipeline.add_step(imager)

test_pipeline = Pipeline()
launcher = Launcher()
test_pipeline.add_step(launcher)

pipeline = Pipeline()
pipeline.add_step(build_pipeline)
pipeline.add_step(test_pipeline)

pipeline.execute(build_context)
