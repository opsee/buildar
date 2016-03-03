import boto3, time
from troposphere import Template, Ref, Parameter, Output, Base64
import buildar.helpers.waiters as waiters
import troposphere.ec2 as ec2

from buildar.pipeline.step import Step

class Launcher(Step):
    def __init__(self):
        self._ec2 = boto3.client('ec2')
        self._cfn = boto3.client('cloudformation')

    def _template_json(self, userdata, build_context):
        t = Template()
        ami_id = build_context['image_id']
        build_region = build_context['build_region']
        build_vpc = build_context['build_vpc']
        key_name = build_context['key_name']

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

        instance = ec2.Instance(
            'buildInstance',
            ImageId = ami_id,
            InstanceType = 't2.micro',
            SecurityGroupIds = [ Ref(sg) ],
            KeyName = key_name,
            UserData = Base64(userdata),
        )
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
        ec2 = self._ec2
        userdata = file('userdata', 'r').read()
        stack_name = 'opsee-bastion-build-%s' % int(time.time())

        template = self._template_json(
            userdata,
            build_context
        )
        
        resp = cfn.create_stack(
            StackName=stack_name,
            TemplateBody=template
        )

        stack_id = resp['StackId']
        print 'Test stack id: %s' % stack_id

        print 'Waiting for stack creation to finish...'
        waiter = waiters.CloudFormationWaiter()
        waiter.wait(stack_name, 'CREATE_COMPLETE')

        stack_resp = cfn.describe_stacks(StackName=stack_name)
        instance_id = stack_resp['Stacks'][0]['Outputs'][0]['OutputValue']

        print 'Waiting for build instance (%s) to become available...' % instance_id
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        public_ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']
        print 'Got instance public IP: %s' % public_ip
        return build_context

    def cleanup(self, build_context):
        pass
