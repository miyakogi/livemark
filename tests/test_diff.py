#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from livemark.diff import _is_same_node, _next_noempty

from wdom.tests.util import TestCase
from wdom.parser import parse_html


class TestSameNode(TestCase):
    def setUp(self):
        self.src1 = '<h1>text1</h1>'
        self.src2 = '<h1>text2</h1>'
        self.src3 = '<h2>text1</h2>'
        self.text1 = 'text1'
        self.text2 = 'text2'
        self.node1 = parse_html(self.src1).firstChild
        self.node2 = parse_html(self.src2).firstChild
        self.node3 = parse_html(self.src3).firstChild
        self.t_node1 = parse_html(self.text1).firstChild
        self.t_node2 = parse_html(self.text2).firstChild

    def test_same_node(self):
        node1 = parse_html(self.src1).firstChild
        node2 = parse_html(self.src1).firstChild
        self.assertTrue(_is_same_node(node1, node2))

    def test_different_text(self):
        self.assertFalse(_is_same_node(self.node1, self.node2))

    def test_different_tag(self):
        self.assertFalse(_is_same_node(self.node1, self.node3))

    def test_same_text(self):
        node1 = parse_html(self.text1).firstChild
        node2 = parse_html(self.text1).firstChild
        self.assertTrue(_is_same_node(node1, node2))

    def test_different_text_node(self):
        self.assertFalse(_is_same_node(self.t_node1, self.t_node2))

    def test_different_tag_text(self):
        self.assertFalse(_is_same_node(self.node1, self.t_node1))
        self.assertFalse(_is_same_node(self.node2, self.t_node2))
        self.assertFalse(_is_same_node(self.node3, self.t_node1))
