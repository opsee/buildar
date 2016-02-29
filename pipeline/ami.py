import boto3

ec2 = boto3.client('ec2')

class Ami(object):
    def __init__(self):
        pass

    def build(self):
        response = ec2.describe_instances(InstanceIds=[ instance_id ])
        volume_id = response['Reservations'][0]['Instances'][0]['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        print 'Build instance root volume id: %s' % volume_id

        print 'Waiting for root volume snapshot to be ready...'
        response = ec2.create_snapshot(VolumeId=volume_id, Description='bastion ami')
        snapshot_id = response['SnapshotId']

        waiter = ec2.get_waiter('snapshot_completed')
        waiter.wait(SnapshotIds=[snapshot_id])

        print 'Registering snapshot as AMI...'
        response = ec2.register_image(
                Name='Opsee-Bastion-%s' % time.time(),
                Description='Opsee Bastion Software',
                RootDeviceName='/dev/xvda',
                VirtualizationType='hvm',
                Architecture='x86_64',
                BlockDeviceMappings=[
                    {
                        'DeviceName': '/dev/xvda',
                        'Ebs': {
                            'SnapshotId': snapshot_id,
                            'DeleteOnTermination': True,
                            'VolumeType': 'standard',
                        }
                    },
                ])

        image_id = response['ImageId']
        print 'Registered %s as %s' % (snapshot_id, image_id)

        print 'Waiting for AMI to be available...'
        waiter = ec2.get_waiter('image_available')
        waiter.wait(ImageIds=[image_id])

        print ec2.describe_images(ImageIds=[image_id])
