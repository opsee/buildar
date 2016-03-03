"""Launch will launch a bastion given a previously-created AMI ID in the build_context."""

import time

import boto3
from troposphere import Template, Ref, Output, Base64
import troposphere.ec2 as ec2

import buildar.helpers.waiters as waiters
from buildar.pipeline.step import Step

#pylint: disable=duplicate-code
def template_json(userdata, build_context):
    """Get a CloudFormation template for a given build_context.

    Requires:
    build_context['image_id']
    build_context['build_vpc']
    build_context['key_name']
    """
    template = Template()
    ami_id = build_context['image_id']
    build_vpc = build_context['build_vpc']
    key_name = build_context['key_name']

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
        ImageId=ami_id,
        InstanceType='t2.micro',
        SecurityGroupIds=[Ref(secgroup)],
        KeyName=key_name,
        UserData=Base64(userdata),
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

class Launcher(Step):
    """Launcher launches a CloudFormation stack for a new bastion given a
    previously-built AMI."""

    def __init__(self):
        super
        self._ec2 = boto3.client('ec2')
        self._cfn = boto3.client('cloudformation')

    def build(self, build_context):
        """Build launches the previously-built AMI, given a userdata filed called 'userdata'.

        Requires:
        build_context['image_id']
        build_context['build_vpc']
        build_context['key_name']
        """

        userdata = file('userdata', 'r').read()
        stack_name = 'opsee-bastion-build-%s' % int(time.time())
        build_context['launch_stack_name'] = stack_name

        template = template_json(
            userdata,
            build_context
        )

        resp = self._cfn.create_stack(
            StackName=stack_name,
            TemplateBody=template
        )

        stack_id = resp['StackId']
        print 'Test stack id: %s' % stack_id

        print 'Waiting for stack creation to finish...'
        waiter = waiters.CloudFormationWaiter()
        waiter.wait(stack_name, 'CREATE_COMPLETE')

        stack_resp = self._cfn.describe_stacks(StackName=stack_name)
        instance_id = stack_resp['Stacks'][0]['Outputs'][0]['OutputValue']

        print 'Waiting for build instance (%s) to become available...' % instance_id
        waiter = self._ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        public_ip = self._ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]\
                ['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']
        print 'Got instance public IP: %s' % public_ip
        return build_context

    def cleanup(self, build_context):
        if self.cleanup:
            print 'Cleaning up launch/test stack...'
            self._cfn.delete_stack(StackName=build_context['launch_stack_name'])

