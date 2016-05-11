import time

import boto3
from botocore.exceptions import ClientError

from buildar.pipeline.step import Step

class Publisher(Step):
    def build(self, build_context):
        self.images = []
        self._ec2 = boto3.client('ec2', region_name=build_context['build_region'])
        regions = self._ec2.describe_regions()['Regions']
        build_image_id = build_context['image_id']

        for r in regions:
            region_name = r['RegionName']
            region_client = boto3.client('ec2', region_name=region_name)
            
            if region_name != build_context['build_region']:
                print 'Publishing bastion AMIs %s' % region_name
                resp = region_client.copy_image(
                    SourceRegion=build_context['build_region'],
                    SourceImageId=build_image_id,
                    Name=build_context['image_name'],
                    Description='Opsee Bastion software'
                )
                image_id = resp['ImageId']
            else:
                image_id = build_image_id

            time.sleep(5)
            region_client.create_tags(Resources=[image_id],
                Tags=[
                    {
                        'Key': 'release',
                        'Value': 'stable'
                    },
                    {
                        'Key': 'sha',
                        'Value': build_context['bastion_version']
                    },
                    {
                        'Key': 'opsee',
                        'Value': 'bastion'
                    }
                ]
            )

        build_context

    def cleanup(self, build_context):
        build_context
