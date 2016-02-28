#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from os import path
import json
import asyncio
import webbrowser
from functools import partial

from tornado import web
from tornado import websocket
from tornado.platform.asyncio import AsyncIOMainLoop

from pygments.styles import STYLE_MAP
from pygments.formatters import HtmlFormatter

current_dir = path.dirname(__file__)
sys.path.insert(0, path.dirname(current_dir))
sys.path.insert(0, path.join(path.dirname(current_dir), 'wdom'))

from wdom import options
from wdom.tag import Div, Style, H2, Script, WebElement
from wdom.document import get_document
from wdom.server import get_app, start_server
from wdom.parser import parse_html

from livemark.diff import find_diff_node
from livemark.converter import convert


cursor_move_js = '''
        function moveToElement(id) {
            var elm = document.getElementById(id)
            if (elm) {
                var x = window.scrollX
                var rect = elm.getBoundingClientRect()
                window.scrollTo(x, rect.top + window.scrollY)
            }
        }
    '''

options.parser.define('browser', default='google-chrome', type=str)
options.parser.define('browser-port', default=8089, type=int)
options.parser.define('vim-port', default=8090, type=int)
options.parser.define('js-files', default=[], nargs='+')
options.parser.define('css-files', default=[], nargs='+')
options.parser.define('highlight-theme', default='default', type=str)


class MainHandler(web.RequestHandler):
    def get(self):
        self.render('main.html', css=css, port=options.config.browser_port)


class SocketListener(asyncio.Protocol):
    pass


class Preview(Div):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tlist = []
        self.dom_tree = None
        self._tasks = []

    def _canncel_tasks(self):
        for task in self._tasks:
            if not task.done() and not task.cancelled():
                task.cancel()
            self._tasks.remove(task)

    def data_received(self, data):
        self._canncel_tasks()
        line = data['line']
        event = data['event']
        if event == 'update':
            self.tlist = data['text']
            _task = self.update_preview
        elif event == 'move':
            _task = self.move_cursor
        else:
            raise ValueError('Get unknown event: {}'.format(event))
        try:
            self._tasks.append(asyncio.ensure_future(_task(line)))
        except asyncio.CancelledError:
            pass

    @asyncio.coroutine
    def update_preview(self, line):
        html = yield from self.convert_to_html(self.tlist)
        yield from self.mount_html(html)
        yield from self.move_cursor(line)

    @asyncio.coroutine
    def convert_to_html(self, tlist):
        md = '\n'.join(tlist)
        yield from asyncio.sleep(0.0)
        return convert(md)

    @asyncio.coroutine
    def mount_html(self, html):
        fragment = parse_html(html)
        self.dom_tree = fragment.cloneNode(True)
        if self.length < 1:
            self.appendChild(fragment)
        else:
            diff = yield from find_diff_node(self, fragment)
            for _i in diff['inserted']:
                self.insertBefore(_i[1], _i[0])
            for _d in diff['deleted']:
                self.removeChild(_d)
            for _a in diff['appended']:
                self.appendChild(_a)

    @asyncio.coroutine
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
                if isinstance(top_node, WebElement):
                    self.move_to(top_node.id)
                else:
                    while top_node is not None:
                        top_node = top_node.previousSibling
                        if isinstance(top_node, WebElement):
                            self.move_to(top_node.id)
                            break

    def move_to(self, id):
        script = 'moveToElement("{}")'.format(id)
        self.js_exec('eval', script=script)


class SocketServer(object):
    def __init__(self, address='localhost', port=8090, loop=None, preview=None):
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
    AsyncIOMainLoop().install()

    doc = get_document()
    doc.title = 'LiveMark'
    _user_static_dirs = set()
    for js in options.config.js_files:
        _user_static_dirs.add(path.dirname(js))
        doc.add_jsfile(js)
    for css in options.config.css_files:
        _user_static_dirs.add(path.dirname(css))
        doc.add_cssfile(css)

    # choices arg is better, but detecting error is not easy in livemark.vim
    if options.config.highlight_theme in STYLE_MAP:
        pygments_style = HtmlFormatter(
            style=options.config.highlight_theme).get_style_defs()
    else:
        pygments_style = HtmlFormatter('default').get_style_defs()
    doc.head.appendChild(Style(pygments_style))

    script = Script(parent=doc.body)
    script.textContent = cursor_move_js
    preview = Preview(parent=doc.body, class_='container')
    preview.appendChild(H2('LiveMark is running...'))
    app = get_app(doc)
    for _d in _user_static_dirs:
        app.add_static_path(_d, _d)
    web_server = start_server(app, port=options.config.browser_port)

    loop = asyncio.get_event_loop()
    sock_server = SocketServer(port=options.config.vim_port, loop=loop,
                               preview=preview)
    browser = webbrowser.get(options.config.browser)
    browser.open('http://localhost:{}'.format(options.config.browser_port))
    try:
        sock_server.start()
        loop.run_forever()
    except KeyboardInterrupt:
        sock_server.stop()
        web_server.stop()


if __name__ == '__main__':
    options.parse_command_line()
    main()
