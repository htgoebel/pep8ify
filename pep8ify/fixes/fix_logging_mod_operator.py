from lib2to3.fixer_base import BaseFix
from lib2to3.pgen2 import token
from lib2to3.fixer_util import (
    Comma, Name, Call, LParen, RParen, Dot, Node, Leaf,
    ArgList, String, syms, is_tuple)
from lib2to3 import patcomp
from lib2to3.pytree import type_repr

from lib2to3.pygram import python_symbols as symbols

import sys

from .fix_logging_format_string import FixLoggingFormatString, should_be_processed, get_args

found = set()

"""

self.error('result' %s)

Node(power, [
    Leaf(1, u'self'),
    Node(trailer,
         [Leaf(23, u'.'),
          Leaf(1, u'error')]),
    Node(trailer,
         [Leaf(7, u'('),
          Node(term,
               [Leaf(3, u"'result'"),
                Leaf(24, u'%'),
                Leaf(1, u'a')]),
          Leaf(8, u')')])])

After convertion
Node(power,
     [ Leaf(1, u'self'),
       Node(trailer,
            [Leaf(23, u'.'),
             Leaf(1, u'error')]),
       Node(trailer,
            [Leaf(7, u'('),
             Leaf(3, u"'result'"),
             Leaf(12, u','),
             Leaf(1, u'a'),
             Leaf(8, u')')])])

"""


_modterm_pattern = patcomp.compile_pattern("""
    term=term< left=any '%' right=any >
    """)

class FixLoggingModOperator(FixLoggingFormatString):

    PATTERN = """
    power< 'self'
      trailer< '.' ( 'log' | 'warning' | 'info' | 'critical' | 'debug'
                     | 'error' | 'exception' | 'fatal' | 'warn' | 'msg'
             ) >
      trailer< '(' ( term=term< left=any '%' right=any >
                   | args=arglist )
                ')'
      >
      any*
    >
    """

    def replace_by_args(self, term, args):
        parent = term.parent
        if parent.type == syms.arglist:
            pos = term.remove()
            for j, a in enumerate(args):
                parent.insert_child(pos+j, a.clone())
        elif parent.type == syms.trailer:
            pos = term.remove()
            parent.insert_child(pos, Node(syms.arglist,
                                          (a.clone() for a in args)))
        else:
            print >>sys.stderr
            print >>sys.stderr, repr(term.parent)
            print >>sys.stderr
            raise SystemExit(1)

    def carry_over_prefix(self, node):
        from_ = node
        to = node.next_sibling
        if to is None and node.parent:
            to = node.parent
        fp = from_.prefix or ''
        tp = to.prefix or ''
        if fp.replace(' ', '') == tp.replace(' ', ''):
            if len(fp) > len(tp):
                fp, tp = '', fp
            else:
                fp, tp = '', tp
        to.prefix = fp + tp

    def fix_term(self, term, left, right, **kw):
        assert isinstance(left, Leaf) and left.type == token.STRING
        self.carry_over_prefix(left.next_sibling)
        if isinstance(right, Node) and right.type == syms.atom:
            args = right.children[:]
            assert args[0] == LParen()
            assert args[-1] == RParen()
            self.carry_over_prefix(args[0])
            self.carry_over_prefix(args[-1])
            args = args[1:-1]
        else:
            args = [right]
        args = [left, Comma()] + args
        self.replace_by_args(term, args)
        

    def transform(self, node, results):
        if not should_be_processed(node):
            return
        if results.has_key('term'):
            self.fix_term(**results)
        else:
            for a in results['args'].children:
                res = {}
                if _modterm_pattern.match(a, res):
                    print str(node)#[:75]
                    #self.fix_term(**res)
            return
        return
        # now fix the format string
        res = {}
        p = patcomp.compile_pattern(FixLoggingFormatString.PATTERN)
        assert p.match(node, res)
        FixLoggingFormatString.transform(self, node, res)
