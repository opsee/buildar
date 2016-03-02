from buildar.pipeline.cloudformation import Builder
from buildar.pipeline.provision import Provisioner
from buildar.pipeline.ami import Imager

class Pipeline(object):
    def __init__(self):
        self._steps = []

    def add_step(self, step):
        self._steps.append(step)

    def execute(self, build_context):
        executed = []
        current_step = ''
        try:
            for step in self._steps:
                current_step = type(step).__name__
                executed.append(step)
                build_context = step.build(build_context)

        except Exception as e:
            print 'Build failed at step %s: %s' % (current_step, e)
        
        for step in executed:
            try:
                step.cleanup(build_context)
            except Exception as e:
                print 'Cleanup step %s failed: %s' % (type(step).__name__, e)
