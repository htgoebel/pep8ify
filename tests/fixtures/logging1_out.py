
import logging


class C():
    def e(self):
        pass
c = C()
a = b = 1


class X(object, log.Loggable):
    def x():
        logging.debug('%s %r %s', 1, a + b, c.e())
        logging.info('%s %r %s', 1, a + b, c.e())
        logging.error('%s %s %s', 1, a + b, c.e())
