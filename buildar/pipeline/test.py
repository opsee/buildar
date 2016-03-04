"""Test will test an instance to ensure that everything is running as it should
be."""

from buildar.pipeline.step import Step

class Tester(Step):
    def __init__(self):
        super

    def build(self, build_context):
        return build_context

    def cleanup(self, build_context):
        if self.do_cleanup:
            pass
