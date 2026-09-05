"""Read a WeChatDataAnalysis HTML export without extracting the archive."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup


def load_messages(archive_path: Path) -> tuple[dict, list[dict]]:
    with zipfile.ZipFile(archive_path) as archive:
        meta_name = next(
            name for name in archive.namelist() if name.startswith("conversations/") and name.endswith("/meta.json")
        )
        html_name = next(
            name for name in archive.namelist() if name.startswith("conversations/") and name.endswith("/messages.html")
        )
        meta = json.loads(archive.read(meta_name).decode("utf-8"))
        html = archive.read(html_name).decode("utf-8")

    soup = BeautifulSoup(html, "html.parser")
    messages: list[dict] = []
    for node in soup.select("div[data-render-type][data-wce-create-time]"):
        row = node.select_one(".wce-msg-row")
        is_sent = bool(row and "wce-msg-row-sent" in row.get("class", []))
        sender_node = node.select_one(".wce-msg-content > .text-left")
        sender = "我" if is_sent else (sender_node.get_text(" ", strip=True) if sender_node else "未知成员")
        bubble = node.select_one(".msg-bubble")
        render_type = node.get("data-render-type", "")
        content = bubble.get_text("\n", strip=True) if bubble else ""
        if render_type.casefold() == "chathistory":
            content = node.get_text("\n", strip=True)
        links = [link.get("href", "") for link in bubble.select("a[href]") if link.get("href")] if bubble else []
        links.extend(re.findall(r"https?://[^\s<>]+", content))
        links = list(dict.fromkeys(links))
        media = [
            item.get("src", "")
            for item in bubble.select("img[src], video[src], audio[src]")
            if item.get("src")
        ] if bubble else []
        if not content:
            alt_text = [item.get("alt", "") for item in node.select("img[alt]") if item.get("alt")]
            content = " ".join(alt_text).strip()
        messages.append(
            {
                "index": len(messages) + 1,
                "time": node.get("title", ""),
                "timestamp": int(node.get("data-wce-create-time", "0") or 0),
                "date": node.get("data-wce-date", ""),
                "sender": sender,
                "isSent": is_sent,
                "type": render_type,
                "content": re.sub(r"\n{3,}", "\n\n", content),
                "links": links,
                "media": media,
            }
        )
    return meta, messages


def print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--mode", choices=("stats", "chunk", "lines", "search"), default="stats")
    parser.add_argument("--start", type=int, default=1, help="One-based first message index")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--query", default="")
    args = parser.parse_args()

    meta, messages = load_messages(args.archive)
    if args.mode == "stats":
        sender_counts = Counter(message["sender"] for message in messages)
        type_counts = Counter(message["type"] for message in messages)
        text_chars = sum(len(message["content"]) for message in messages)
        print_json(
            {
                "group": meta.get("displayName"),
                "metaMessageCount": meta.get("messageCount"),
                "parsedMessageCount": len(messages),
                "firstTime": messages[0]["time"] if messages else None,
                "lastTime": messages[-1]["time"] if messages else None,
                "textCharacters": text_chars,
                "senders": sender_counts.most_common(),
                "types": type_counts,
                "messagesWithLinks": sum(bool(message["links"]) for message in messages),
                "messagesWithMedia": sum(bool(message["media"]) for message in messages),
            }
        )
        return

    if args.mode == "search":
        query = args.query.casefold()
        selected = [
            message
            for message in messages
            if query in message["content"].casefold() or query in message["sender"].casefold()
        ][: args.limit]
        print_json({"query": args.query, "count": len(selected), "messages": selected})
        return

    start = max(0, args.start - 1)
    selected = messages[start : start + max(1, args.limit)]
    if args.mode == "lines":
        for message in selected:
            content = message["content"].replace("\r", "").replace("\n", " ↩ ")
            print(
                f"#{message['index']}\t{message['time']}\t{message['sender']}\t"
                f"{message['type']}\t{content}"
            )
        return
    compact = [
        {
            "index": message["index"],
            "time": message["time"],
            "sender": message["sender"],
            "type": message["type"],
            "content": message["content"],
            "links": message["links"],
            "media": message["media"],
        }
        for message in selected
    ]
    print_json({"start": args.start, "count": len(compact), "messages": compact})


if __name__ == "__main__":
    main()
