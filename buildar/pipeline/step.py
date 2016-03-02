class Step(object):
    def run(self, build_context):
        raise NotImplemented('Sub-classes must implement cleanup()')

    def cleanup(self, build_context):
        raise NotImplemented('Sub-classes must implement cleanup()')
