"""AWS Waiters that are missing from boto3 go here."""

import time
import re

import boto3
from botocore.exceptions import ClientError

class CloudFormationWaiter(object):
    """A simple waiter for CloudFormation stacks."""

    POLL_PERIOD = 30
    MAX_RETRIES = 20

    def __init__(self, client):
        self._cfn = client

    def wait(self, stack_name, state):
        """Wait for a stack, identified by name, to reach a given state.
        
        Provides a waiter for a fake state 'DELETE_COMPLETE'
        """

        cstate = ''
        i = 0
        while i < self.MAX_RETRIES:
            try:
                # Throws a botocore.exceptions.ClientError if stack does not exist.
                resp = self._cfn.describe_stacks(StackName=stack_name)
                cstate = resp['Stacks'][0]['StackStatus']
                if cstate == state:
                    return
                else:
                    i += 1
                    time.sleep(self.POLL_PERIOD)
            except ClientError as ex:
                # Most likely the stack wasn't found, so we return.
                if ex.message.endswith('does not exist') and state == 'DELETE_COMPLETE':
                    return
                else:
                    raise ex

        msg = 'Timed out waiting on state. Stuck in state: %s' % cstate
        raise Exception(msg)

class RolePolicyWaiter(object):
    """A simple waiter for IAM RolePolicies."""

    POLL_PERIOD = 30
    MAX_RETRIES = 10

    def __init__(self, client):
        self._iam = client

    def wait(self, role_name, policy_name, **kwargs):
        i = 0
        while i < self.MAX_RETRIES:
            try:
                resp = self._iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                # Raises an unhandled KeyError if we get a weird response.
                if resp['RoleName'] == role_name:
                    return
            except ClientError as ex:
                if re.match('.*NoSuchEntity.*', ex.message) != None:
                    time.sleep(self.POLL_PERIOD)
                    i += 1
                else:
                    raise

        msg = 'Timed out waiting for IAM Role created.'
        raise Exception(msg)
