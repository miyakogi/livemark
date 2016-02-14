#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import misaka as m
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, PythonLexer


class HighlighterRenderer(m.HtmlRenderer):
    def blockcode(self, text, lang):
        if not lang:
            return '\n<pre><code>{}</code></pre>\n'.format(text)
        else:
            lexer = get_lexer_by_name('python', stripall=True)
            lexer = PythonLexer()
            formatter = HtmlFormatter()
            html = highlight(text, lexer, formatter)
            return html


convert = m.Markdown(HighlighterRenderer(), extensions=(
    'fenced-code', 'tables',
))
