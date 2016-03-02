import time

from troposphere import Template, Ref, Parameter, Output
import troposphere.ec2 as ec2
import requests
import boto3

import buildar.helpers.waiters as waiters
from buildar.pipeline.step import Step

class Key(object):
    def __init__(self, aws_key):
        self.name = aws_key['KeyName']
        self.fingerprint = aws_key['KeyFingerprint']
        self.key = aws_key['KeyMaterial']

class Builder(Step):
    COREOS_URL = 'https://coreos.com/dist/aws/aws-beta.json'
    VIRT_TYPE = 'hvm'

    def __init__(self):
        self._ec2 = boto3.client('ec2')
        self._cfn = boto3.client('cloudformation')

    def _latest_ami(self, build_region):
        resp = requests.get(self.COREOS_URL)
        resp.close()
        return resp.json()[build_region][self.VIRT_TYPE]

    def _create_key_pair(self, stack_name):
        return self._ec2.create_key_pair(KeyName=stack_name)

    def template_json(self, build_region, build_vpc):
        t = Template()

        sg = ec2.SecurityGroup('buildSecurityGroup')
        sg.GroupDescription = 'Bastion build security group'
        sg.SecurityGroupIngress = [
            {
                'CidrIp': '0.0.0.0/0',
                'FromPort': 22,
                'ToPort': 22,
                'IpProtocol': "tcp",
            },
        ]
        sg.SecurityGroupEgress = [
            {
                'CidrIp': '0.0.0.0/0',
                'FromPort': -1,
                'ToPort': -1,
                'IpProtocol': -1,
            },
        ]
        sg.VpcId = build_vpc
        t.add_resource(sg)

        instance = ec2.Instance('buildInstance')
        instance.ImageId = self._latest_ami(build_region)
        instance.InstanceType = 't2.micro'
        instance.SecurityGroupIds = [ Ref(sg) ]
        instance.KeyName = self.key.name
        t.add_resource(instance)

        t.add_output([
            Output(
                "BuildInstanceId",
                Description="Build instance ID",
                Value=Ref(instance)
            ),
        ])

        return t.to_json()

    def build(self, build_context):
        cfn = self._cfn
        print 'Launching build stack'
        stack_name = 'opsee-bastion-build-%s' % int(time.time())

        self.key = Key(self._create_key_pair(stack_name))
        build_context['key_name'] = self.key.name

        resp = cfn.create_stack(
            StackName=stack_name,
            TemplateBody=self.template_json(
                build_context['build_region'], 
                build_context['build_vpc']),
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

        build_context['instance_id'] = instance_id
        build_context['ssh_key'] = self.key.key

        public_ip = ec2.describe_instances(InstanceIds=[build_context['instance_id']])['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']
        print 'Got instance public IP: %s' % public_ip
        build_context['public_ip'] = public_ip
        build_context['stack_name'] = stack_name

        return build_context

    def cleanup(self, build_context):
        try:
            self._ec2.delete_key_pair(KeyName=build_context['key_name'])
        except Exception as e:
            print 'Failed to delete KeyPair: %s' % e
        try:
            self._cfn.delete_stack(StackName=build_context['stack_name'])
        except Exception as e:
            print 'Failed to delete stack: %s' % e
            raise
