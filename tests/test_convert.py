#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from livemark import convert

from wdom.tests.util import TestCase


class TestMarkdown(TestCase):
    def test_markdown(self):
        self.assertEqual(convert('# Title'), '<h1>Title</h1>\n')

    def test_blank(self):
        self.assertEqual(convert(''), '')

    def test_blankline(self):
        self.assertEqual(convert('\n'), '')

    def test_blanklines(self):
        self.assertEqual(convert('\n\n'), '')

    def test_blankline_in_sentence(self):
        self.assertEqual(convert('a\nb'), '<p>a\nb</p>\n')
        self.assertEqual(convert('a\nb\n'), '<p>a\nb</p>\n')

    def test_2blanklines_in_sentence(self):
        self.assertEqual(convert('a\n\nb'), '<p>a</p>\n\n<p>b</p>\n')
        self.assertEqual(convert('a\n\nb\n'), '<p>a</p>\n\n<p>b</p>\n')

    def test_3blanklines_in_sentence(self):
        self.assertEqual(convert('a\n\n\nb'), '<p>a</p>\n\n<p>b</p>\n')
        self.assertEqual(convert('a\n\n\nb\n'), '<p>a</p>\n\n<p>b</p>\n')
