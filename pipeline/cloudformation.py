from troposphere import Template, Ref, Parameter, Output
import troposphere.ec2 as ec2
import requests

class Builder(object):
    COREOS_URL = 'https://coreos.com/dist/aws/aws-beta.json'
    VIRT_TYPE = 'hvm'

    def __init__(self, region, vpc):
        self.build_vpc = vpc
        self.build_region = region

    def _latest_ami(self):
        resp = requests.get(self.COREOS_URL)
        resp.close()
        return resp.json()[self.build_region][self.VIRT_TYPE]

    def template_json(self):
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
        sg.VpcId = self.build_vpc
        t.add_resource(sg)

        instance = ec2.Instance('buildInstance')
        instance.ImageId = self._latest_ami()
        instance.InstanceType = 't2.micro'
        instance.SecurityGroupIds = [ Ref(sg) ]
        t.add_resource(instance)

        t.add_output([
            Output(
                "BuildInstanceId",
                Description="Build instance ID",
                Value=Ref(instance)
            ),
        ])

        return t.to_json()
