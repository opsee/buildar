"""Launch will launch a bastion given a previously-created AMI ID in the build_context."""

import time
from base64 import standard_b64encode as b64_encode

import boto3
from botocore.exceptions import ClientError
import requests
from troposphere import Template, Ref, Output, Base64
import troposphere.ec2 as ec2
from jinja2 import Template

import buildar.helpers.waiters as waiters
from buildar.pipeline.step import Step

userdata_template = """#cloud-config
write_files:
  - path: "/etc/opsee/bastion-env.sh"
    permissions: "0644"
    owner: "root"
    content: |
      CUSTOMER_ID={{ customer_id }}
      CUSTOMER_EMAIL={{ customer_email }}
      BASTION_ID={{ bastion_id }}
      VPN_PASSWORD={{ vpn_password }}
      VPN_REMOTE=bastion.opsee.com
      DNS_SERVER=169.254.169.253
      NSQD_HOST=nsqd.in.opsee.com:4150
      BARTNET_HOST=https://bartnet.in.opsee.com
      BASTION_AUTH_TYPE=BASIC_TOKEN
      GODEBUG=netdns=cgo
users:
  - name: "opsee"
    groups:
      - "sudo"
      - "docker"
    ssh-authorized-keys:
      - "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDP+VmyztGmJJTe6YtMtrKazGy3tQC/Pku156Ae10TMzCjvtiol+eL11FKyvNvlENM5EWwIQEng5w3J616kRa92mWr9OWALBn4HJZcztS2YLAXyiC+GLauil6W6xnGzS0DmU5RiYSSPSrmQEwHvmO2umbG190srdaDn/ZvAwptC1br/zc/7ya3XqxHugw1V9kw+KXzTWSC95nPkhOFoaA3nLcMvYWfoTbsU/G08qQy8medqyK80LJJntedpFAYPUrVdGY2J7F2y994YLfapPGzDjM7nR0sRWAZbFgm/BSD0YM8KA0mfGZuKPwKSLMtTUlsmv3l6GJl5a7TkyOlK3zzYtVGO6dnHdZ3X19nldreE3DywpjDrKIfYF2L42FKnpTGFgvunsg9vPdYOiJyIfk6lYsGE6h451OAmV0dxeXhtbqpw4/DsSHtLm5kKjhjRwunuQXEg8SfR3kesJjq6rmhCjLc7bIKm3rSU07zbXSR40JHO1Mc9rqzg2bCk3inJmCKWbMnDvWU1RD475eATEKoG/hv0/7EOywDnFe1m4yi6yZh7XlvakYsxDBPO9/FMlZm2T+cn+TyTmDiw9tEAIEAEiiu18CUNIii1em7XtFDmXjGFWfvteQG/2A98/uDGbmlXd64F2OtU/ulDRJXFGaji8tqxQ/To+2zIeIptLjtqBw=="
update:
  reboot-strategy: "off"
  group: "beta"
"""

assume_role_policy = '''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": ["ec2.amazonaws.com"]
      },
      "Action": [ "sts:AssumeRole" ]
    }
  ]
}
'''

def get_bucket_path(region, obj):
    host = 's3.amazonaws.com' if region == 'us-east-1' else 's3.%s.amazonaws.com' % region
    return '/'.join([
        'https://%s' % host,
        'opsee-bastion-cf-%s' % region,
        'beta',
        obj])

class Launcher(Step):
    """Launcher launches a CloudFormation stack for a new bastion given a
    previously-built AMI."""

    def build(self, build_context):
        """Build launches the previously-built AMI.

        Requires:
        build_context['image_id']
        build_context['build_vpc']
        build_context['build_region']
        build_context['key_name']
        build_context['customer_id']
        build_context['customer_email']
        build_context['basiton_id']
        build_context['vpn_password']
        """

        self._ec2 = boto3.client('ec2', region_name=build_context['build_region'])
        self._cfn = boto3.client('cloudformation', region_name=build_context['build_region'])
        self._iam = boto3.client('iam', region_name=build_context['build_region'])
        self._as = boto3.client('autoscaling', region_name=build_context['build_region'])

        customer_id = build_context['customer_id']
        build_time = int(time.time())
        stack_name = 'opsee-stack-%s' % customer_id
        role_name = 'opsee-role-%s' % customer_id
        policy_name = 'opsee-policy-%s' % customer_id

        resp = requests.get(get_bucket_path(build_context['build_region'], 'opsee-role.json'))
        policy = resp.text

        self._iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=assume_role_policy)
        self._iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=policy)

        build_context['role_name'] = role_name

        build_context['policy_name'] = policy_name

        userdata_t = Template(userdata_template)
        userdata = b64_encode(userdata_t.render(
            customer_id=build_context['customer_id'],
            bastion_id=build_context['bastion_id'],
            customer_email=build_context['customer_email'],
            vpn_password=build_context['vpn_password'],
        ))

        build_context['launch_stack_name'] = stack_name

        resp = self._ec2.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id', 
                    'Values':[build_context['build_vpc']]
                }, 
                {
                    'Name': 'availabilityZone', 
                    # ${reigon}a is almost always going to exist. We can get AZs and pick one
                    # later if we need to.
                    'Values': ['%sa' % build_context['build_region']]
                }, 
                {
                    'Name': 'defaultForAz', 
                    'Values': ['true']
                },
            ]
        )
        subnet_id = resp['Subnets'][0]['SubnetId']
        build_context['launch_subnet_id'] = subnet_id

        resp = self._cfn.create_stack(
            StackName=stack_name,
            TemplateURL=get_bucket_path(build_context['build_region'], 'bastion-cf.template'),
            Capabilities=['CAPABILITY_IAM'],
            Parameters=[
                {
                    'ParameterKey': 'AllowSSH',
                    'ParameterValue': 'True',
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'ImageId',
                    'ParameterValue': build_context['image_id'],
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'UserData',
                    'ParameterValue': userdata,
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'KeyName',
                    'ParameterValue': build_context['key_name'],
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'VpcId',
                    'ParameterValue': build_context['build_vpc'],
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'SubnetId',
                    'ParameterValue': subnet_id,
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'CustomerId',
                    'ParameterValue': stack_name,
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'BastionId',
                    'ParameterValue': stack_name,
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'OpseeRole',
                    'ParameterValue': role_name,
                    'UsePreviousValue': False,
                },
                {
                    'ParameterKey': 'BastionIngressTemplateUrl',
                    'ParameterValue': get_bucket_path(build_context['build_region'], 'bastion-ingress-cf.template'),
                    'UsePreviousValue': False,
                },
            ],
        )

        stack_id = resp['StackId']
        print 'Test stack id: %s' % stack_id

        print 'Waiting for stack creation to finish...'
        waiter = waiters.CloudFormationWaiter(self._cfn)
        waiter.wait(stack_name, 'CREATE_COMPLETE')

        resources = self._cfn.describe_stack_resources(StackName=stack_name)
        asg_id = [x for x in resources['StackResources'] if x['ResourceType'] == 'AWS::AutoScaling::AutoScalingGroup'][0]['PhysicalResourceId']
        resp = self._as.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_id])
        instance_id = resp['AutoScalingGroups'][0]['Instances'][0]['InstanceId']

        print 'Waiting for build instance (%s) to become available...' % instance_id
        waiter = self._ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        public_ip = self._ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]\
                ['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']
        print 'Got instance public IP: %s' % public_ip
        build_context['launch_public_ip'] = public_ip

        print 'Sleeping for 240 seconds to allow bastion to finish initialization...'
        time.sleep(240)

        return build_context

    def cleanup(self, build_context):
        if self.do_cleanup:
            print 'Cleaning up launch/test stack...'
            stack_name = build_context['launch_stack_name']
            self._cfn.delete_stack(StackName=stack_name)

            waiter = waiters.CloudFormationWaiter(self._cfn)
            waiter.wait(stack_name, 'DELETE_COMPLETE')
            self._iam.delete_role_policy(RoleName=build_context['role_name'], PolicyName=build_context['policy_name'])
            self._iam.delete_role(RoleName=build_context['role_name'])
