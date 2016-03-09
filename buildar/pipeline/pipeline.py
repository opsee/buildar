"""
A Pipeline is a collection of Steps that are executed in the order
they are added to the Pipeline. Upon execution of a Step, the Pipeline
marks the step for rollback, s.t. if a step fails halfway through its
duties, it has the opportunity to attempt to clean everything up.

A Pipeline is also a Step and can be embedded in other pipelines.
"""

#pylint: disable=unused-import
from buildar.pipeline.step import Step
from buildar.pipeline.builder import Builder
from buildar.pipeline.provision import Provisioner
from buildar.pipeline.ami import Imager
from buildar.pipeline.launch import Launcher
from buildar.pipeline.test import Tester

class Pipeline(Step):
    """Pipeline can be used to encapsulate a set of steps or used as a step
    itself.  Steps' build phases are run in the order that they are added to a
    Pipeline with add_step, but the cleanup phases of those steps are executed
    in reverse order, s.t. the output that a step depends on from the previous
    step still exists in an unaltered state."""

    def __init__(self, **kwargs):
        super(Pipeline, self).__init__(**kwargs)
        self._steps = []
        self._executed = []
        self._failed = False
        self._exception_cause = StandardError()

    def add_step(self, step):
        """Add a step to the pipeline. Must implement the missing methods of
        the Step base class."""

        self._steps.append(step)

    def build(self, build_context):
        """Build iterates over the steps in the pipeline and executes them
        in order"""

        current_step = ''

        try:
            for step in self._steps:
                current_step = type(step).__name__
                self._executed.append(step)
                build_context = step.build(build_context)
        except Exception as ex:
            print 'Build failed at step %s: %s' % (current_step, ex)
            self._exception_cause = ex
            self._failed = True

        return build_context

    def cleanup(self, build_context):
        """Cleanup iterates over the steps that the pipeline attempted to
        execute in the reverse order that they were executed. It raises
        the exception of the failed build step if a step failed during
        build().
        
        Pipelines adhere to cleanup of all steps included in the pipeline. You
        can either set cleanup=True/False on individual steps or on the
        pipeline. This can also be done in combination. If you want to cleanup
        all but one step in a pipeline, you can set the Pipeline cleanup to
        True, and then set that individual step's cleanup to False."""

        if self.do_cleanup:
            self._executed.reverse()
            for step in self._executed:
                try:
                    step.cleanup(build_context)
                except Exception as ex:
                    print 'Cleanup step %s failed: %s' % (type(step).__name__, ex)

            if self._failed:
                raise self._exception_cause

    def execute(self, build_context):
        """Execute is a convenience function that ties build and cleanup together."""

        build_context = self.build(build_context)
        self.cleanup(build_context)

