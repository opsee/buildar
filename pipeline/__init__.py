class Pipeline(object):
    def __init__(self):
        self._pos = 0
        self._steps = []

    def add_step(self, step):
        self._steps.append(step)

    def run(self):
        for step in self.steps:
            try:
                step.run()
            except Exception as e:
                print 'Step %s failed, rolling back...' % step.name
                step.rollback()
