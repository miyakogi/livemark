#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from syncer import sync

from livemark.diff import _is_same_node, _next_noempty, find_diff_node

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


class TextFindDiffNode(TestCase):
    def setUp(self):
        self.src_list = ['<h{0}>text{0}</h{0}>'.format(x) for x in range(1, 7)]
        self.html = '\n'.join(self.src_list)
        self.base_node = parse_html(self.html)

    def assertEmpty(self, target):
        self.assertEqual(len(target), 0)

    @sync
    async def test_same_tree(self):
        new_node = parse_html(self.html)
        diff = await find_diff_node(self.base_node, new_node)
        self.assertEmpty(diff.get('deleted'))
        self.assertEmpty(diff.get('inserted'))
        self.assertEmpty(diff.get('appended'))

    @sync
    async def test_append_end(self):
        new_html = self.html + '\n<h1>text7</h1>'
        new_node = parse_html(new_html)
        diff = await find_diff_node(self.base_node, new_node)
        self.assertEmpty(diff.get('deleted'))
        self.assertEmpty(diff.get('inserted'))
        self.assertEqual(len(diff.get('appended')), 1)

    @sync
    async def test_delete_end(self):
        new_html = self.html.replace('<h6>text6</h6>', '')
        new_node = parse_html(new_html)
        diff = await find_diff_node(self.base_node, new_node)
        self.assertEqual(len(diff.get('deleted')), 1)
        self.assertEmpty(diff.get('inserted'))
        self.assertEmpty(diff.get('appended'))

    @sync
    async def test_insert_first(self):
        new_html = '<h1>text0</h1>\n' + self.html
        new_node = parse_html(new_html)
        diff = await find_diff_node(self.base_node, new_node)
        self.assertEmpty(diff.get('deleted'))
        self.assertEqual(len(diff.get('inserted')), 1)
        self.assertEmpty(diff.get('appended'))
