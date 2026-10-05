"""Export a Claude Code session log (.jsonl) to a readable, redacted Markdown transcript.

Usage:
    python tools/export_session.py [path/to/session.jsonl] [--out session-export/]

Keeps user messages, Claude's replies, tool calls (summarised) and short tool results.
Drops internal reasoning blocks, harness metadata, base64 images and system reminders.
Redacts cloud identifiers, IPs, tokens, local user paths and the teammate's name.
"""
import argparse
import glob
import json
import os
import pathlib
import re

PROJECT_LOGS = pathlib.Path.home() / ".claude" / "projects" / "D--hackathons-amazon-raksham"

REDACTIONS = [
    # secrets (defence in depth: none should be present)
    (r"hf_[A-Za-z0-9]{20,}", "<HF_TOKEN>"),
    (r"sk-[A-Za-z0-9_\-]{20,}", "<API_KEY>"),
    (r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "<AWS_ACCESS_KEY>"),
    (r"\bgh[pousr]_[A-Za-z0-9*]{20,}", "<GITHUB_TOKEN>"),
    (r"Bearer\s+[A-Za-z0-9\-_.=]{20,}", "Bearer <TOKEN>"),
    # cloud identifiers
    (r"arn:aws:[A-Za-z0-9\-]*:[A-Za-z0-9\-]*:\d{12}:[^\s\"'`|)]+", "<AWS_ARN>"),
    (r"301745146083", "<AWS_ACCOUNT_ID>"),
    (r"\b(i|sg|key|lt|ami|vpc|subnet|vol|eni|snap)-[0-9a-f]{8,17}\b", r"<\1-id>"),
    (r"\b(?:crossart|crosslang|seamledger)-\d{4}-\d{2}-\d{2}-[\d-]+", "<other-project-job>"),
    (r"\bpytorch-training-\d{4}-\d{2}-\d{2}-[\d-]+", "<other-project-job>"),
    # network
    (r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b", "<IP>"),
    # local identity
    (r"(?i)[A-Z]:[\\/]+Users[\\/]+Galaba Vamsi", "C:/Users/<user>"),
    (r"(?i)/c/Users/Galaba Vamsi", "/c/Users/<user>"),
    (r"GALABA~1", "<user>"),
    (r"b9603e3c-1555-426e-ba7f-0e88d2d72962", "<session-id>"),
    (r"\ba[0-9a-f]{16}\b", "<agent-id>"),
    # teammate privacy
    (r"(?i)Varun Rai", "[Teammate]"),
    (r"(?i)varun", "[Teammate]"),
]

RESIDUAL_CHECKS = {
    "aws account": r"\b\d{12}\b(?=.*(?:aws|arn|account))",
    "ipv4": r"\b(?!127\.0\.0\.1)(?:\d{1,3}\.){3}\d{1,3}\b",
    "hf token": r"hf_[A-Za-z0-9]{20,}",
    "openai key": r"sk-[A-Za-z0-9_\-]{20,}",
    "aws key": r"AKIA[0-9A-Z]{16}",
    "user path": r"Users[\\/]Galaba",
    "teammate": r"Varun",
}


def redact(text: str) -> str:
    for pat, rep in REDACTIONS:
        text = re.sub(pat, rep, text)
    return text


def clip(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n].rstrip() + f"\n… [{len(text) - n:,} more characters truncated]"


def strip_harness(text: str) -> str:
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", text, flags=re.S)
    return text.strip()


def fence(body: str, lang: str = "") -> str:
    body = body.replace("```", "ˋˋˋ")
    return f"```{lang}\n{body}\n```"


def summarise_tool_use(name: str, inp: dict) -> str:
    if name == "Bash":
        desc = inp.get("description", "")
        return f"**Bash** — {desc}\n\n" + fence(clip(inp.get("command", ""), 1500), "bash")
    if name in ("Write",):
        content = inp.get("content", "")
        lines = content.count("\n") + 1
        return f"**Write** `{inp.get('file_path')}` ({lines} lines)\n\n" + fence(clip(content, 1800))
    if name == "Edit":
        return (f"**Edit** `{inp.get('file_path')}`\n\n- old: " + fence(clip(inp.get("old_string", ""), 400))
                + "\n- new: " + fence(clip(inp.get("new_string", ""), 600)))
    if name == "Read":
        return f"**Read** `{inp.get('file_path')}`"
    if name == "Agent":
        return (f"**Spawned agent** — *{inp.get('description', '')}* ({inp.get('subagent_type', 'default')})\n\n"
                + fence(clip(inp.get("prompt", ""), 5000)))
    if name == "SendMessage":
        return f"**Message to agent** — *{inp.get('summary', '')}*\n\n" + fence(clip(inp.get("message", ""), 3000))
    if name == "AskUserQuestion":
        out = ["**Asked the user**"]
        for q in inp.get("questions", []):
            opts = " · ".join(o.get("label", "") for o in q.get("options", []))
            out.append(f"- {q.get('question')}  \n  options: {opts}")
        return "\n".join(out)
    if name.startswith("mcp__aws-mcp__aws___run_script"):
        return "**AWS (MCP run_script)**\n\n" + fence(clip(inp.get("code", ""), 1500), "python")
    if name.startswith("mcp__"):
        return f"**{name.split('__')[-1]}** — " + clip(json.dumps(inp, ensure_ascii=False), 600)
    return f"**{name}** — " + clip(json.dumps(inp, ensure_ascii=False), 600)


def summarise_tool_result(block: dict) -> str:
    c = block.get("content")
    parts = []
    if isinstance(c, str):
        parts.append(c)
    elif isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
            elif isinstance(b, dict) and b.get("type") == "image":
                parts.append("[image]")
    text = "\n".join(parts)
    if "Async agent launched successfully" in text:
        return "_[background agent launched]_"
    if text.startswith("Message queued for delivery") or '"success":true' in text[:40]:
        return "_[message delivered]_"
    text = strip_harness(text)
    if not text:
        return ""
    return "<details><summary>result</summary>\n\n" + fence(clip(text, 1200)) + "\n\n</details>"


def render_user_text(text: str) -> str | None:
    if "<agent-message from=" in text:
        body = re.sub(r"(?s).*?<agent-message from=\"[^\"]+\">", "", text)
        body = re.sub(r"(?s)</agent-message>.*", "", body)
        body = re.sub(r"(?m)^\s*\[Subagent hand-back\].*?The report follows:\s*$", "", body, flags=re.S)
        body = "\n".join(line[2:] if line.startswith("  ") else line for line in body.splitlines())
        return "### Sub-agent report\n\n" + clip(body.strip(), 6000)
    if "<task-notification>" in text:
        m = re.search(r"<summary>(.*?)</summary>", text, flags=re.S)
        return f"_[notification: {m.group(1).strip() if m else 'background task update'}]_"
    if "<command-name>" in text:
        name = re.search(r"<command-name>(.*?)</command-name>", text)
        args = re.search(r"<command-args>(.*?)</command-args>", text, flags=re.S)
        rest = re.sub(r"<command-[a-z]+>.*?</command-[a-z]+>", "", text, flags=re.S)
        rest = strip_harness(rest)
        out = f"### User\n\n`{name.group(1) if name else ''}` {args.group(1).strip() if args else ''}"
        return out + (f"\n\n{rest}" if rest else "")
    if "<bash-input>" in text:
        return "### User (shell)\n\n" + fence(strip_harness(re.sub(r"</?bash-[a-z]+>", "\n", text)), "text")
    text = strip_harness(text)
    if not text or text.startswith("[SYSTEM NOTIFICATION"):
        return None
    if "sent a new message while you were working" in text:
        text = re.sub(r"(?s)^The user sent a new message while you were working:\s*", "", text)
        text = re.sub(r"(?s)\n\nThis is how Claude Code surfaces.*", "", text)
    return "### User\n\n" + text


def export(src: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    out = [
        "# Claude Code session: building *Pehchaan* for the RAKSHAM AI-cybersecurity hackathon",
        "",
        "> Exported from the Claude Code session log. Internal reasoning, harness metadata and images are omitted; "
        "long tool outputs are truncated. Cloud identifiers, IP addresses, tokens, local paths and a teammate's name are redacted.",
        "",
    ]
    turns = {"user": 0, "assistant_text": 0, "tool_calls": 0, "agents": 0}
    with open(src, encoding="utf-8") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") == "attachment":
                a = o.get("attachment") or {}
                if a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human" and a.get("prompt"):
                    out += ["### User (sent while Claude was working)", "", strip_harness(str(a["prompt"])), ""]
                    turns["user"] += 1
                continue
            if o.get("type") not in ("user", "assistant") or o.get("isSidechain"):
                continue
            m = o.get("message") or {}
            role, content = m.get("role"), m.get("content")
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                t = b.get("type")
                if role == "user" and t == "text":
                    r = render_user_text(b.get("text", ""))
                    if r:
                        out += [r, ""]
                        turns["user"] += r.startswith("### User")
                elif role == "user" and t == "tool_result":
                    r = summarise_tool_result(b)
                    if r:
                        out += [r, ""]
                elif role == "user" and t == "image":
                    out += ["_[image attached by user]_", ""]
                elif role == "assistant" and t == "text" and b.get("text", "").strip():
                    out += ["### Claude", "", b["text"].strip(), ""]
                    turns["assistant_text"] += 1
                elif role == "assistant" and t == "tool_use":
                    out += [summarise_tool_use(b.get("name", ""), b.get("input", {}) or {}), ""]
                    turns["tool_calls"] += 1
                    turns["agents"] += b.get("name") == "Agent"
    md = redact("\n".join(out))
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / "pehchaan-claude-code-session.redacted.md"
    dst.write_text(md, encoding="utf-8")
    print(f"wrote {dst} ({dst.stat().st_size // 1024} KB)")
    print("counts:", turns)
    for label, pat in RESIDUAL_CHECKS.items():
        hits = re.findall(pat, md, flags=re.I)
        print(f"  residual {label:12s}: {len(hits)}" + (f"  e.g. {hits[:3]}" if hits else ""))
    return dst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("--out", default="session-export")
    a = ap.parse_args()
    src = pathlib.Path(a.src) if a.src else max(map(pathlib.Path, glob.glob(str(PROJECT_LOGS / "*.jsonl"))), key=os.path.getsize)
    export(src, pathlib.Path(a.out))
