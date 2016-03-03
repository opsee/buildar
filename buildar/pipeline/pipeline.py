from buildar.pipeline.cloudformation import Builder
from buildar.pipeline.provision import Provisioner
from buildar.pipeline.ami import Imager
from buildar.pipeline.launch import Launcher
from buildar.pipeline.step import Step

class Pipeline(Step):
    """
    A Pipeline is a collection of Steps that are executed in the order
    they are added to the Pipeline. Upon execution of a Step, the Pipeline
    marks the step for rollback, s.t. if a step fails halfway through its
    duties, it has the opportunity to attempt to clean everything up.

    A Pipeline is also a Step and can be embedded in other pipelines.
    """
    def __init__(self):
        self._steps = []
        self._executed = []
        self._exception_cause = None

    def add_step(self, step):
        self._steps.append(step)

    def build(self, build_context):
        current_step = ''
        exception_cause = None
        
        try:
            for step in self._steps:
                current_step = type(step).__name__
                self._executed.append(step)
                build_context = step.build(build_context)
        except Exception as e:
            print 'Build failed at step %s: %s' % (current_step, e)
            self._exception_cause = e

        return build_context

    def cleanup(self, build_context):
        for step in self._executed.reverse():
            try:
                step.cleanup(build_context)
            except Exception as e:
                print 'Cleanup step %s failed: %s' % (type(step).__name__, e)
            
        if self._exception_cause is not None:
            raise self._exception_cause 

    def execute(self, build_context):
        build_context = self.build(build_context)
        self.cleanup(build_context)
        
