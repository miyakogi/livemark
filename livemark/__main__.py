#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from os import path
import json
import asyncio

from tornado import web  # type: ignore

from pygments.styles import STYLE_MAP
from pygments.formatters import HtmlFormatter  # type: ignore

current_dir = path.dirname(__file__)
sys.path.insert(0, path.dirname(current_dir))
sys.path.insert(0, path.join(path.dirname(current_dir), 'wdom'))

from wdom.options import config, parser, parse_command_line
from wdom.tag import Div, Style, H2, Script, WdomElement
from wdom.document import get_document
from wdom.server import start_server, add_static_path
from wdom.parser import parse_html
from wdom.util import install_asyncio

from livemark.diff import find_diff_node
from livemark.converter import convert


cursor_move_js = '''
        function moveToElement(id) {
            var elm = document.querySelector('[rimo_id="' + id + '"]')
            if (elm) {
                var x = window.scrollX
                var rect = elm.getBoundingClientRect()
                window.scrollTo(x, rect.top + window.scrollY)
            }
        }
    '''

parser.add_argument('--vim-port', default=8090, type=int)
parser.add_argument('--js-files', default=[], nargs='+', type=str)
parser.add_argument('--css-files', default=[], nargs='+', type=str)
parser.add_argument('--highlight-theme', default='default', type=str)
parse_command_line()


class SocketListener(asyncio.Protocol):
    pass


class Preview(Div):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tlist = []
        self.dom_tree = None

    def data_received(self, data):
        line = data['line']
        event = data['event']
        if event == 'update':
            self.tlist = data['text']
            _task = self.update_preview
        elif event == 'move':
            _task = self.move_cursor
        else:
            raise ValueError('Get unknown event: {}'.format(event))
        _task(line)

    def update_preview(self, line):
        html = self.convert_to_html(self.tlist)
        self.mount_html(html)
        self.move_cursor(line)

    def convert_to_html(self, tlist):
        md = '\n'.join(tlist)
        return convert(md)

    def mount_html(self, html):
        fragment = parse_html(html)
        self.dom_tree = fragment.cloneNode(True)
        if self.length < 1:
            self.appendChild(fragment)
        else:
            diff = find_diff_node(self, fragment)
            for _i in diff['inserted']:
                self.insertBefore(_i[1], _i[0])
            for _d in diff['deleted']:
                self.removeChild(_d)
            for _a in diff['appended']:
                self.appendChild(_a)

    def move_cursor(self, line):
        if line < 0:
            return

        blank_lines = 0
        i = 1
        while i < line and i < len(self.tlist):
            if self.tlist[i] == '' and self.tlist[i - 1] == '':
                blank_lines += 1
            i += 1
        cur_line = line - blank_lines

        node_n = 0
        if self.dom_tree is not None and self.ownerDocument:
            _l = 0
            elm = self.dom_tree.firstChild
            while elm is not None:
                if elm.nodeName != '#text':
                    node_n += 1
                _l += elm.textContent.count('\n')
                if _l >= cur_line:
                    break
                elm = elm.nextSibling

            if node_n >= len(self):
                top_node = self.lastChild
            else:
                top_node = self.childNodes[node_n - 1]
            if top_node is not None:
                if isinstance(top_node, WdomElement):
                    self.move_to(top_node.rimo_id)
                else:
                    while top_node is not None:
                        top_node = top_node.previousSibling
                        if isinstance(top_node, WdomElement):
                            self.move_to(top_node.rimo_id)
                            break

    def move_to(self, id):
        script = 'moveToElement("{}")'.format(id)
        self.js_exec('eval', script)


class SocketServer(object):
    def __init__(self, address='localhost', port=8090, loop=None,
                 preview=None):
        self.address = address
        self.port = port
        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop
        self.preview = preview

        self.listener = SocketListener
        self.listener.connection_made = self.connection_made
        self.listener.data_received = self.data_received
        self.transport = None

    def start(self):
        self.coro_server = self.loop.create_server(self.listener, self.address,
                                                   self.port)
        self.server_task = self.loop.run_until_complete(self.coro_server)
        return self.server_task

    def stop(self):
        self.server_task.close()

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.transport.close()
        msg = json.loads(data.decode())[1]
        self.preview.data_received(msg)


def main():
    install_asyncio()

    doc = get_document()
    doc.title = 'LiveMark'
    _user_static_dirs = set()
    for js in config.js_files:
        _user_static_dirs.add(path.dirname(js))
        doc.add_jsfile(js)
    for css in config.css_files:
        _user_static_dirs.add(path.dirname(css))
        doc.add_cssfile(css)

    # choices arg is better, but detecting error is not easy in livemark.vim
    if config.highlight_theme in STYLE_MAP:
        pygments_style = HtmlFormatter(
            style=config.highlight_theme).get_style_defs()
    else:
        pygments_style = HtmlFormatter('default').get_style_defs()
    doc.head.appendChild(Style(pygments_style))

    script = Script(parent=doc.body)
    script.textContent = cursor_move_js
    preview = Preview(parent=doc.body, class_='container')
    preview.appendChild(H2('LiveMark is running...'))
    for _d in _user_static_dirs:
        add_static_path(_d, _d)
    web_server = start_server()

    loop = asyncio.get_event_loop()
    sock_server = SocketServer(port=config.vim_port, loop=loop,
                               preview=preview)
    try:
        sock_server.start()
        loop.run_forever()
    except KeyboardInterrupt:
        sock_server.stop()
        web_server.stop()


if __name__ == '__main__':
    main()
