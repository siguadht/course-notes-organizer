#!/usr/bin/env python3
"""Validate the minimum structure of a generated course-notes HTML file."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class NotesParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.title_depth = 0
        self.title_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "a" and (values.get("href") or "").startswith("#"):
            self.links.append((values.get("href") or "")[1:])
        if tag == "title":
            self.title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_text.append(data.strip())


def validate(text: str) -> list[str]:
    errors: list[str] = []
    parser = NotesParser()
    parser.feed(text)
    required = {"html", "head", "title", "body", "header", "nav", "main", "section", "h1", "h2"}
    missing = sorted(required - parser.tags)
    if not re.match(r"\s*<!doctype html>", text, re.I):
        errors.append("缺少 <!doctype html>。")
    if missing:
        errors.append("缺少语义元素：" + ", ".join(missing))
    if not "".join(parser.title_text).strip():
        errors.append("title 不能为空。")
    duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
    if duplicates:
        errors.append("存在重复 id：" + ", ".join(duplicates))
    broken = sorted({target for target in parser.links if target not in parser.ids})
    if broken:
        errors.append("目录锚点不存在：" + ", ".join(broken))
    if re.search(r"\{\{[^}]+\}\}", text):
        errors.append("仍有未替换的模板标记。")
    if re.search(r"<(script|link)\b", text, re.I):
        errors.append("HTML 应保持单文件且无外部脚本或样式依赖。")
    return errors


def self_test() -> int:
    good = """<!doctype html><html><head><title>课程</title></head><body><header><h1>课程</h1></header><nav><a href='#a'>一</a></nav><main><section id='a'><h2>一</h2></section></main></body></html>"""
    bad = "<html><head><title>{{TITLE}}</title></head><body></body></html>"
    return 0 if not validate(good) and validate(bad) else 1


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("path", nargs="?", type=Path)
    cli.add_argument("--self-test", action="store_true")
    args = cli.parse_args()
    if args.self_test:
        return self_test()
    if not args.path:
        cli.error("请提供 HTML 文件路径，或使用 --self-test。")
    text = args.path.read_text(encoding="utf-8")
    errors = validate(text)
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("OK: HTML 结构、目录锚点和模板替换检查通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
