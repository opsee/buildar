"""Setup the build instance for the bastion."""

import time

from troposphere import Template, Ref, Output
import troposphere.ec2 as ec2
import requests
import boto3

import buildar.helpers.waiters as waiters
from buildar.pipeline.step import Step

#pylint: disable=duplicate-code
class Builder(Step):
    """Builder is responsible for launching the CloudFormation stack that
    creates the base CoreOS instance used to build the bastion."""

    COREOS_URL = 'https://coreos.com/dist/aws/aws-beta.json'
    VIRT_TYPE = 'hvm'

    def __init__(self, **kwargs):
        super(Builder, self).__init__(**kwargs)
        self.key = {}

    def _latest_ami(self, build_region):
        resp = requests.get(self.COREOS_URL)
        resp.close()
        return resp.json()[build_region][self.VIRT_TYPE]

    def _create_key_pair(self, stack_name):
        self.key = self._ec2.create_key_pair(KeyName=stack_name)
        return self.key

    def template_json(self, build_region, build_vpc):
        """Get the CloudFormation template for the build instance."""

        template = Template()

        secgroup = ec2.SecurityGroup('buildSecurityGroup')
        secgroup.GroupDescription = 'Bastion build security group'
        secgroup.SecurityGroupIngress = [
            {
                'CidrIp': '0.0.0.0/0',
                'FromPort': 22,
                'ToPort': 22,
                'IpProtocol': "tcp",
            },
        ]
        secgroup.SecurityGroupEgress = [
            {
                'CidrIp': '0.0.0.0/0',
                'FromPort': -1,
                'ToPort': -1,
                'IpProtocol': -1,
            },
        ]
        secgroup.VpcId = build_vpc
        template.add_resource(secgroup)

        instance = ec2.Instance(
            'buildInstance',
            ImageId=self._latest_ami(build_region),
            InstanceType='t2.micro',
            SecurityGroupIds=[Ref(secgroup)],
            KeyName=self.key['KeyName'],
        )
        template.add_resource(instance)

        template.add_output([
            Output(
                "BuildInstanceId",
                Description="Build instance ID",
                Value=Ref(instance)
            ),
        ])

        return template.to_json()

    def build(self, build_context):
        build_region = build_context['build_region']

        self._ec2 = boto3.client('ec2', region_name=build_region)
        self._cfn = boto3.client('cloudformation', region_name=build_region)

        print 'Launching build stack'
        stack_name = 'opsee-bastion-build-%s' % int(time.time())

        self._create_key_pair(stack_name)
        build_context['key_name'] = self.key['KeyName']

        time.sleep(5)
        resp = self._cfn.create_stack(
            StackName=stack_name,
            TemplateBody=self.template_json(
                build_context['build_region'],
                build_context['build_vpc']),
            )

        stack_id = resp['StackId']
        print 'Build stack id: %s' % stack_id

        print 'Waiting for stack creation to finish...'
        waiter = waiters.CloudFormationWaiter(self._cfn)
        waiter.wait(stack_name, 'CREATE_COMPLETE')

        stack_resp = self._cfn.describe_stacks(StackName=stack_name)
        instance_id = stack_resp['Stacks'][0]['Outputs'][0]['OutputValue']

        print 'Waiting for build instance (%s) to become available...' % instance_id
        waiter = self._ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        build_context['instance_id'] = instance_id
        build_context['ssh_key'] = self.key['KeyMaterial']

        public_ip = self._ec2.describe_instances(InstanceIds=[build_context['instance_id']])['Reservations'][0]\
                ['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']
        print 'Got instance public IP: %s' % public_ip
        build_context['public_ip'] = public_ip
        build_context['stack_name'] = stack_name

        return build_context

    def cleanup(self, build_context):
        if self.do_cleanup:
            try:
                self._ec2.delete_key_pair(KeyName=build_context['key_name'])
            except StandardError as ex:
                print 'Failed to delete KeyPair: %s' % ex
            try:
                self._cfn.delete_stack(StackName=build_context['stack_name'])
            except StandardError as ex:
                print 'Failed to delete stack: %s' % ex
                raise
