import boto3

from buildar.pipeline.step import Step

class Tagger(Step):
    def build(self, build_context):
        self._ec2 = boto3.client('ec2', region_name=build_context['build_region'])
        regions = self._ec2.describe_regions()['Regions']

        published_images = build_context.get('published_images', {})

        for r in regions:
            print 'Tagging image in region %s' % r['RegionName']
            region_name = r['RegionName']
            region_client = boto3.client('ec2', region_name=region_name)

            image_id = published_images.get(region_name, '')
            release = build_context.get('release_tag', '')
            sha = build_context.get('bastion_version', '')

            if image_id == '' or release == '' or sha == '':
                resp = region_client.describe_images(
                        Filters=[
                            {
                                'Name': 'name',
                                'Values': [build_context['image_name']],
                            },
                        ])

                image = resp['Images'][0]
                image_id = image['ImageId']

                tags = image.get('Tags', [])
                release_tags = [x for x in tags if x['Key'] == 'release']
                sha_tags = [x for x in tags if x['Key'] == 'sha']

                if release == '' and len(release_tags) > 0:
                    release = release[0]['Value']
                else:
                    release = "beta"

                if sha == '' and len(sha_tags) > 0:
                    sha = sha[0]['Value']
                elif sha == '':
                    sha = "unknown"

            region_client.create_tags(Resources=[image_id],
                    Tags=[
                        {
                            'Key': 'release',
                            'Value': build_context.get('release_tag', release),
                        },
                        {
                            'Key': 'sha',
                            'Value': build_context.get('bastion_version', sha),
                        },
                        {
                            'Key': 'opsee',
                            'Value': 'bastion',
                        },
                    ])

        return build_context

    def cleanup(self, build_context):
        return build_context
