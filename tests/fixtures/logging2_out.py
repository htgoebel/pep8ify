
import logging


class C():
    def e(self):
        pass
c = C()
a = b = 1


class X(object, log.Loggable):
    def x():
        self.debug('result %s %s', a, b)
        self.debug('result %s %s', a + b, c.e())
        self.info('result %s', a + b)
        self.error('result %s', a)
        #self.debug('result %s' % a, c.e()) # unhandled case

        self.debug('result %s', a, c)
