#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio

from wdom.tag import WebElement


def _is_same_node(node1:WebElement, node2:WebElement):
    if node1.nodeType == node2.nodeType:
        if node1.nodeType in (node1.TEXT_NODE, node1.COMMENT_NODE):
            return node1.textContent == node2.textContent
        else:
            return node1.html_noid == node2.html_noid
    else:
        return False


def _next_noempty(node:WebElement):
    new_node = node.nextSibling
    while new_node is not None:
        if isinstance(new_node, WebElement):
            return new_node
        else:
            text = new_node.textContent
            if text and not text.isspace():
                return new_node
            new_node = new_node.nextSibling
    return None


@asyncio.coroutine
def find_diff_node(base_node:WebElement, new_node:WebElement):
    _deleted = []
    _inserted = []
    _appended = []

    node1 = base_node.firstChild
    node2 = new_node.firstChild
    last_node2 = node2
    while node1 is not None and last_node2 is not None:  # Loop over old html
        yield from asyncio.sleep(0.0)
        if _is_same_node(node1, node2):
            node1 = _next_noempty(node1)
            node2 = _next_noempty(node2)
            last_node2 = node2
        else:
            _pending = [node2]
            while True:  # Loop over new html
                node2 = node2.nextSibling
                if node2 is None:
                    _deleted.append(node1)
                    node1 = _next_noempty(node1)
                    node2 = last_node2
                    break
                elif _is_same_node(node1, node2):
                    for n in _pending:
                        _inserted.append((node1, n))
                    node1 = _next_noempty(node1)
                    node2 = _next_noempty(node2)
                    last_node2 = node2
                    break
                else:
                    _pending.append(node2)

    if node1 is not None:
        n = node1
        while n is not None:
            _deleted.append(n)
            n = _next_noempty(n)
    elif last_node2 is not None:
        n = last_node2
        while n is not None:
            _appended.append(n)
            n = _next_noempty(n)

    return {'deleted': _deleted, 'inserted': _inserted,
            'appended': _appended}
