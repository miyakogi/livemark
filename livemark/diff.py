#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio

from wdom.tag import WebElement


def is_same_node(node1:WebElement, node2:WebElement):
    if node1.nodeType == node2.nodeType:
        if node1.nodeType in (node1.TEXT_NODE, node1.COMMENT_NODE):
            return node1.textContent == node2.textContent
        else:
            return node1.html_noid == node2.html_noid
    else:
        return False


def is_empty_text_node(node:WebElement):
    if isinstance(node, WebElement):
        return False
    text = node.textContent
    return not text or text.isspace()


def next_noempty(node:WebElement):
    new_node = node.nextSibling
    while new_node is not None:
        if not is_empty_text_node(new_node):
            return new_node
        else:
            new_node = new_node.nextSibling
    return None


@asyncio.coroutine
def find_diff_node(base_node:WebElement, new_node:WebElement):
    _deleted = []
    _inserted = []
    _appended = []

    node1 = base_node.firstChild
    node2 = new_node.firstChild
    if is_empty_text_node(node1):
        node1 = next_noempty(node1)
    if is_empty_text_node(node2):
        node2 = next_noempty(node2)
    last_node2 = node2
    while node1 is not None and last_node2 is not None:  # Loop over old html
        yield from asyncio.sleep(0.0)
        if is_same_node(node1, node2):
            node1 = next_noempty(node1)
            node2 = next_noempty(node2)
            last_node2 = node2
        else:
            _pending = [node2]
            while True:  # Loop over new html
                node2 = next_noempty(node2)
                if node2 is None:
                    _deleted.append(node1)
                    node1 = next_noempty(node1)
                    node2 = last_node2
                    break
                elif is_same_node(node1, node2):
                    for n in _pending:
                        _inserted.append((node1, n))
                    node1 = next_noempty(node1)
                    node2 = next_noempty(node2)
                    last_node2 = node2
                    break
                else:
                    _pending.append(node2)

    if node1 is not None:
        n = node1
        while n is not None:
            _deleted.append(n)
            n = next_noempty(n)
    elif last_node2 is not None:
        n = last_node2
        while n is not None:
            _appended.append(n)
            n = next_noempty(n)

    return {'deleted': _deleted, 'inserted': _inserted,
            'appended': _appended}
