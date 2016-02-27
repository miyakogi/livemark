#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from livemark.diff import _is_same_node, _next_noempty

from wdom.tests.util import TestCase
from wdom.parser import parse_html


class TestSameNode(TestCase):
    def test_same_node(self):
        node1_src = '<h1>A</h1>'
        node1 = parse_html(node1_src)
        node2 = parse_html(node1_src)
        self.assertTrue(_is_same_node(node1.firstChild, node2.firstChild))
