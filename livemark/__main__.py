#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from os import path
import json
import asyncio

from pygments.styles import STYLE_MAP  # type: ignore
from pygments.formatters import HtmlFormatter  # type: ignore

current_dir = path.dirname(__file__)
try:
    import wdom  # noqa
except ImportError:
    sys.path.insert(0, path.dirname(current_dir))
    sys.path.insert(0, path.join(path.dirname(current_dir), 'wdom'))

from wdom.options import config, parser, parse_command_line  # noqa: F401
from wdom.themes import default  # noqa: E402
from wdom.themes.default import Div, Style, H2, Script, RawHtmlNode  # noqa
from wdom.document import get_document  # noqa: F401
from wdom.server import start_server, add_static_path  # noqa: F401
from wdom.util import install_asyncio  # noqa: F401

from livemark.converter import convert  # noqa: F401


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
        self.current_view = H2('LiveMark is running...', parent=self)

    def data_received(self, data):
        line = data['line']
        event = data['event']
        if event == 'update':
            self.tlist = data['text']
            self.update_preview(line)
        elif event == 'move':
            self.move(data['command'].lower())
        else:
            raise ValueError('Get unknown event: {}'.format(event))

    def update_preview(self, line):
        html = self.convert_to_html(self.tlist)
        self.mount_html(html)

    def convert_to_html(self, tlist):
        md = '\n'.join(tlist)
        return convert(md)

    def mount_html(self, html):
        old_view = self.current_view
        self.current_view = RawHtmlNode(html)
        self.replaceChild(self.current_view, old_view)

    def move(self, cmd):
        if cmd == 'top':
            self.exec('window.scrollTo(0, 0)')
        elif cmd == 'bottom':
            self.exec(
                'window.scrollTo(0, document.body.getClientRects()[0].height)')
        elif cmd == 'page_up':
            self.exec('window.scrollBy(0, - window.innerHeight * 0.9)')
        elif cmd == 'page_down':
            self.exec('window.scrollBy(0, window.innerHeight * 0.9)')
        elif cmd == 'half_up':
            self.exec('window.scrollBy(0, - window.innerHeight * 0.45)')
        elif cmd == 'half_down':
            self.exec('window.scrollBy(0, window.innerHeight * 0.45)')
        elif cmd == 'up':
            self.exec('window.scrollBy(0, -50)')
        elif cmd == 'down':
            self.exec('window.scrollBy(0, 50)')


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
    doc.register_theme(default)
    doc.title = 'LiveMark'

    # choices arg is better, but detecting error is not easy in livemark.vim
    if config.highlight_theme in STYLE_MAP:
        pygments_style = HtmlFormatter(
            style=config.highlight_theme).get_style_defs()
    else:
        pygments_style = HtmlFormatter('default').get_style_defs()
    doc.head.appendChild(Style(pygments_style))

    script = Script(parent=doc.body)
    script.textContent = cursor_move_js
    preview = Preview(style='padding: 3rem 10vw;')
    doc.body.appendChild(preview)
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
