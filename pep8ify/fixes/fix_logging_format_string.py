from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token
from lib2to3.fixer_util import (
    Comma, Name, Call, LParen, RParen, Dot, Node, Leaf,
    ArgList, String, syms, is_tuple, find_root)
from lib2to3 import patcomp
from lib2to3.pygram import python_symbols as symbols

import operator


def find_class(node):
    "Find the classdef containing this node."
    while node.type != syms.classdef:
        node = node.parent
        if not node:
            return None
    return node


def get_args(node):
    "Get the elements of an arglist."
    args = node.children[:]
    comma = Comma()
    while args:
        assert args[0] != comma, args[0]
        yield args.pop(0)
        if args:
            assert args[0] == comma, args[0]
            args.pop(0)


_classddef_pattern = patcomp.compile_pattern("""
classdef<
  'class' any '(' classes=arglist<any+> ')'
   any*
  >
""")

def get_superclasses(node):
    "Get the names of the super classes this class is inheriting from."
    results = {}
    if not _classddef_pattern.match(node, results):
        return []
    classes = get_args(results['classes'])
    #print repr(list(classes))
    return [str(cls).strip() for cls in classes]


def should_be_processed(node):
    # If this is not a subclass og 'log.Loggable', ignore it.
    klass = find_class(node)
    if klass is None:
        return False
    superclasses = get_superclasses(klass)
    if not 'log.Loggable' in superclasses:
        return False
    return True


class FixLoggingFormatString(BaseFix):
    """
    Convert
       self.LOGGING('message'   , a1, a2,)
       self.LOGGING('message %s', a1, a2, a3)
    into
       self.LOGGING('message %s %s'   , a1, a2)
       self.LOGGING('message %s %s %s', a1, a2, a3)
    """

    PATTERN = """
    power< any
      trailer< '.' ( 'log' | 'warning' | 'info' | 'critical' | 'debug'
                     | 'error' | 'exception' | 'fatal' | 'warn' | 'msg'
             ) >
      trailer< '(' args=arglist ')'
      >
      any*
    >
    """

    def transform(self, node, results):
        if not should_be_processed(node):
            return

        args = list(get_args(results['args']))
        #print len(args), args
        num_args = len(args)-1
        try:
            fmt = eval(args[0].value)
        except AttributeError:
            print repr(args[0]), dir(args[0])
            return
        a = tuple([1] * num_args)
        #print fmt, num_args, a

        # now test if the format covers all arguments
        try:
            operator.mod(fmt, a)
        except Exception, e:
            #print e
            pass
        else:
            #print 'okay', node.get_lineno(), fmt
            # format already okay, nothing to change
            return

        fmt = self.fix_format(fmt, a)
        args[0].value = repr(fmt)
        node.changed()

    def fix_format(self, fmt, args):
        # append ' %s' for each argument not covered
        for i in range(20): # upper limit
            try:
                operator.mod(fmt, args)
            except TypeError, e:
                if 'not all arguments' in str(e):
                    fmt += ' %s'
                elif 'not enough arguments' in str(e):
                    assert i == 1
                    break
            else:
                break
        return fmt
