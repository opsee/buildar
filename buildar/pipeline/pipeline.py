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

    def add_step(self, step):
        self._steps.append(step)

    def execute(self, build_context):
        executed = []
        current_step = ''
        exception_cause = None

        try:
            for step in self._steps:
                current_step = type(step).__name__
                executed.append(step)
                build_context = step.build(build_context)
        except Exception as e:
            print 'Build failed at step %s: %s' % (current_step, e)
            exception_cause = e
        
        for step in executed:
            try:
                step.cleanup(build_context)
            except Exception as e:
                print 'Cleanup step %s failed: %s' % (type(step).__name__, e)
            
        if exception_cause is not None:
            raise exception_cause 
