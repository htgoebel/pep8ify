from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token
from lib2to3.fixer_util import (
    Comma, Name, Call, LParen, RParen, Dot, Node, Leaf,
    ArgList, String, syms, is_tuple, find_root)
from lib2to3 import patcomp
from lib2to3.pygram import python_symbols as symbols

import operator
import sys
import re


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


_classdef_pattern = patcomp.compile_pattern("""
classdef<
  'class' name=any '(' (classes=any) ')'
   any*
  >
""")

def get_superclasses(node):
    "Get the names of the super classes this class is inheriting from."
    results = {}
    if not _classdef_pattern.match(node, results):
        return []
    classes = results['classes']
    if classes.type == syms.arglist:
        classes = get_args(classes)
    else:
        classes = [classes]
    return [str(cls).strip() for cls in classes]


_known_logger_classes = set((
    'log.Loggable', 'Loggable', 'Device', 'Backend',
    'BackendItem', 'BackendStore', 'AbstractBackendStore', 'BaseTranscoder'))
_known_non_logger_classes = set((
    'object', 'tube.TubeConsumerMixin', 'tube.TubePublisherMixin'
    ))

def should_be_processed(node):
    # If this is not a subclass og 'log.Loggable', ignore it.
    klass = find_class(node)
    if klass is None:
        return False
    superclasses = set(get_superclasses(klass))
    superclasses -= _known_non_logger_classes
    if not superclasses:
        # exit early
        return False
    if superclasses & _known_logger_classes:
        return True
    results = {}
    _classdef_pattern.match(klass, results)
    print >> sys.stderr, 'Skipping', results['name'], tuple(superclasses)
    return False


"""

logging.error("%s", a)

Node(power,
     [Leaf(1, u'logging'),
      Node(trailer,
           [Leaf(23, u'.'),
            Leaf(1, u'error')]),
      Node(trailer,
           [Leaf(7, u'('),
            Node(arglist,
                 [Leaf(3, u'"%s"'),
                  Leaf(12, u','),
                  Leaf(1, u'a')]),
            Leaf(8, u')')])])
"""

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
        if num_args < 1:
            # only one argument, nothing to do
            return

        for a in args[1:]:
            if isinstance(a, Leaf) and a.type in (token.NUMBER, token.STRING):
                print >> sys.stderr, 'Interesting argument:'
                print >> sys.stderr, node
                print >> sys.stderr
                return
                break

        try:
            fmt = args[0].value
        except AttributeError:
            print >> sys.stderr, "Unexpected log message:"
            s = re.sub('(\t|\n|\s)+', ' ', str(node))
            print >> sys.stderr, s[:70].rstrip(), '...'
            print >> sys.stderr
            return
        a = tuple([1] * num_args)

        # fix the format strng
        orig_fmt = fmt
        fmt = self.fix_format_string(fmt, a)
        if orig_fmt == fmt:
            # format was already okay, nothing to change
            return

        args[0].value = fmt
        if args[0].prefix and not args[0].prefix.strip():
            args[0].prefix = ''
        node.changed()

    def fix_format_string(self, fmt, args):
        # append ' %s' for each argument not covered
        # Note: not simply append, but put it into the string. This
        # keeps the quoting style (single or double).
        for i in range(20): # upper limit
            try:
                operator.mod(eval(fmt), args)
            except TypeError, e:
                if 'not all arguments' in str(e):
                    #fmt += ' %s'
                    fmt = fmt[:-1] + ' %s' + fmt[-1]
                elif 'not enough arguments' in str(e):
                    assert i == 1
                    break
            else:
                break
        return fmt
