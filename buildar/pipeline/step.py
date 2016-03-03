"""Step is an interface guide for build steps.
"""

class Step(object):
    """Sub-classes should implement run and cleanup. Each function takes
    a build_context dict as an argument. build() must return the build_context.
    """

    def __init__(self, **kwargs):
        self.cleanup = kwargs.get('cleanup', True)

    def build(self, build_context):
        """The build step. Returns build_context."""

        raise NotImplementedError('Sub-classes must implement cleanup()')

    def cleanup(self, build_context):
        """The cleanup step."""

        raise NotImplementedError('Sub-classes must implement cleanup()')
