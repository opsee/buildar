import boto3
import time

class CloudFormationWaiter(object):
    POLL_PERIOD=30
    MAX_RETRIES=10

    def __init__(self):
        self._cfn = boto3.client('cloudformation')

    def wait(self, stack_name, state):
        cstate = ''
        i = 0
        while i < self.MAX_RETRIES:
            resp = self._cfn.describe_stacks(StackName=stack_name)
            cstate = resp['Stacks'][0]['StackStatus']
            if cstate == state:
                return
            else:
                time.sleep(self.POLL_PERIOD)

        if i > self.MAX_RETRIES:
            raise Exception('Timed out waiting on state. Stuck in state: %s' % cstate)
