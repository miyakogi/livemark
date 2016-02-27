#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
