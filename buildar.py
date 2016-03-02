#!/usr/bin/env python

import boto3, sys, time, requests, json

from buildar.pipeline.pipeline import Builder, Provisioner, Imager, Pipeline

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

pipeline = Pipeline()
pipeline.add_step(builder)
pipeline.add_step(provisioner)
pipeline.add_step(imager)

pipeline.execute(build_context)
