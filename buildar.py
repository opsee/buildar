#!/usr/bin/env python

import boto3, sys, time, requests, json

import helpers.waiters as waiters
from pipeline.cloudformation import Builder

build_region = 'us-east-1'
build_vpc = 'vpc-31a0cc54'
cfn = boto3.client('cloudformation')

print 'Launching build stack'

build_template = Builder(build_region, build_vpc)
stack_name = 'Bastion-build-%s' % int(time.time())
resp = cfn.create_stack(
    StackName=stack_name,
    TemplateBody=build_template.template_json(),
)

stack_id = resp['StackId']
print 'Build stack id: %s' % stack_id

print 'Waiting for stack creation to finish...'
waiter = waiters.CloudFormationWaiter()
waiter.wait(stack_name, 'CREATE_COMPLETE')

stack_resp = cfn.describe_stacks(StackName=stack_name)
instance_id = stack_resp['Stacks'][0]['Outputs'][0]['OutputValue']

ec2 = boto3.client('ec2')
print 'Waiting for build instance (%s) to become available...' % instance_id
waiter = ec2.get_waiter('instance_running')
waiter.wait(InstanceIds=[instance_id])

