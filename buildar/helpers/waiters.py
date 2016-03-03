"""AWS Waiters that are missing from boto3 go here."""

import time

import boto3

class CloudFormationWaiter(object):
    """
    A simple waiter for CloudFormation stacks.
    """

    POLL_PERIOD = 30
    MAX_RETRIES = 10

    def __init__(self):
        self._cfn = boto3.client('cloudformation')

    def wait(self, stack_name, state):
        """Wait for a stack, identified by name, to reach a given state."""

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
            msg = 'Timed out waiting on state. Stuck in state: %s' % cstate
            raise Exception(msg)
