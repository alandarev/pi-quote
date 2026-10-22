#!/usr/bin/env python3
"""Real fullscreen selection + Alt+Q, isolated Pi, no model requests."""

import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unicodedata
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("PI_QUOTE_EXTENSION", ROOT / "src/index.ts")).resolve()
OUTPUT = ROOT / "test/e2e/out"
OUTPUT.mkdir(parents=True, exist_ok=True)
CORE = Path(
    subprocess.check_output(
        [
            "node",
            "--input-type=module",
            "-e",
            'import {getPackageDir} from "@earendil-works/pi-coding-agent"; process.stdout.write(getPackageDir());',
        ],
        cwd=ROOT,
        text=True,
    ).strip()
)
MANIFEST = json.loads((CORE / "package.json").read_text())
BIN = MANIFEST["bin"]
CLI = CORE / (BIN if isinstance(BIN, str) else BIN["pi"])
NODE = shutil.which("node")
if not NODE or not shutil.which("tmux"):
    raise SystemExit("Fullscreen test needs Node and tmux on PATH.")
NAME = "quote-test-" + uuid.uuid4().hex[:10]
ENV = {k: v for k, v in os.environ.items() if not k.endswith(("_API_KEY", "_TOKEN"))}
ENV.pop("PI_PACKAGE_DIR", None)
ENV.update(
    {
        "TERM": "xterm-256color",
        "PI_OFFLINE": "1",
        "PI_SKIP_VERSION_CHECK": "1",
        "PI_TELEMETRY": "0",
    }
)


def tmux(*args, check=True):
    return subprocess.run(
        ["tmux", "-L", NAME, "-f", "/dev/null", *args],
        env=ENV,
        text=True,
        capture_output=True,
        check=check,
    )


def raw(text):
    tmux("send-keys", "-t", "test", "-H", *[f"{byte:02x}" for byte in text.encode()])


def wait_for(fn, description, seconds=25):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        result = fn()
        if result:
            return result
        time.sleep(0.1)
    raise AssertionError("Timed out: " + description)


with tempfile.TemporaryDirectory(prefix="quote-selection-tui-") as temporary:
    temp = Path(temporary)
    agent = temp / "agent"
    agent.mkdir()
    (agent / "settings.json").write_text(
        json.dumps(
            {
                "tuiMode": "fullscreen",
                "fullscreenCopyOnSelect": False,
                "packages": [],
                "retry": {"enabled": False},
                "autoCompact": {"enabled": False},
            }
        )
    )
    ENV["PI_CODING_AGENT_DIR"] = str(agent)
    ENV["PI_CODING_AGENT_SESSION_DIR"] = str(temp / "sessions")
    snapshot = temp / "snapshot.json"
    probe = temp / "probe.ts"
    probe.write_text("""import { writeFileSync } from "node:fs";
export default function(pi) {
  let modelCalls = 0;
  // A unique in-process API has no network transport. A hook exception is NOT
  // sufficient: Pi catches before_provider_request errors and may keep sending.
  pi.registerProvider("quote-test", {
    api: "quote-test-blocked",
    baseUrl: "http://127.0.0.1:9",
    apiKey: "synthetic-test-key",
    models: [{
      id: "blocked", name: "Quote test (network disabled)",
      reasoning: false, input: ["text"], contextWindow: 32768, maxTokens: 128,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    }],
    streamSimple() {
      modelCalls++;
      throw new Error("QUOTE_TEST_TRANSPORT_BLOCKED");
    },
  });
  pi.on("session_start", (_event, ctx) => {
    ctx.ui.onTerminalInput((data) => {
      if (data === "\\x1bz") {
        ctx.ui.setEditorText("Intentional test of blocked transport");
        return { consume: true };
      }
      if (data === "\\x1bf") {
        // Display-only transcript filler: no turn, no model request.
        const filler = Array.from({ length: 120 }, (_, i) => `FILLER_${i}`).join("\\n");
        pi.sendMessage({ customType: "quote-test-filler", content: `SCROLL_TARGET epsilon zeta\\n\\n${filler}`, display: true });
        return { consume: true };
      }
      if (data !== "\\x1by") return;
      let view;
      ctx.ui.setWidget("quote-test:probe", (tui) => { view = tui; return { render: () => [], invalidate() {} }; }, { placement: "belowEditor" });
      ctx.ui.setWidget("quote-test:probe", undefined);
      writeFileSync(process.env.QUOTE_TEST_SNAPSHOT, JSON.stringify({
        draft: ctx.ui.getEditorText(), mode: view.mode,
        selection: view.getActiveSelectionText?.() ?? null,
        cursor: view.getFocusedComponent()?.getCursor?.(), modelCalls,
        scrollTop: view.getPrimaryScrollView?.().scrollTop ?? null,
        following: view.getPrimaryScrollView?.().isFollowingEnd ?? null,
        model: ctx.model?.provider + "/" + ctx.model?.id,
        api: ctx.model?.api, idle: ctx.isIdle(),
      }));
      return { consume: true };
    });
  });
}""")
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    session = temp / "session.jsonl"
    entries = [
        {
            "type": "session",
            "version": 3,
            "id": str(uuid.uuid4()),
            "timestamp": stamp,
            "cwd": str(temp),
        },
        {
            "type": "message",
            "id": "fixture1",
            "parentId": None,
            "timestamp": stamp,
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "QUOTE_TARGET alpha beta\n\nSECOND_TARGET gamma delta\n\nUnicode: Привет 世界",
                    }
                ],
                "api": "openai-responses",
                "provider": "openai",
                "model": "gpt-4o",
                "usage": {
                    "input": 0,
                    "output": 0,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 0,
                    "cost": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "total": 0,
                    },
                },
                "stopReason": "stop",
                "timestamp": int(time.time() * 1000),
            },
        },
    ]
    session.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    command = [
        "env",
        "QUOTE_TEST_SNAPSHOT=" + str(snapshot),
        NODE,
        str(CLI),
        "--offline",
        "--provider",
        "quote-test",
        "--model",
        "blocked",
        "--no-context-files",
        "--no-skills",
        "--no-extensions",
        "--no-prompt-templates",
        "--session",
        str(session),
        "--tui-mode",
        "fullscreen",
        "-e",
        str(SOURCE),
        "-e",
        str(probe),
    ]
    shell = shlex.join(command) + "; sleep 30"

    def screen():
        return tmux("capture-pane", "-p", "-t", "test").stdout

    def inspect():
        snapshot.unlink(missing_ok=True)
        raw("\x1by")
        wait_for(snapshot.exists, "probe snapshot")
        return json.loads(snapshot.read_text())

    def select(text):
        lines = screen().splitlines()
        row = next(i for i, line in enumerate(lines) if text in line)
        start = lines[row].index(text)
        # SGR columns are terminal cells, not codepoints; endpoint is inclusive.
        width = sum(
            0
            if unicodedata.combining(c)
            else 2
            if unicodedata.east_asian_width(c) in ("W", "F")
            else 1
            for c in text
        )
        raw(f"\x1b[<0;{start + 1};{row + 1}M")
        raw(f"\x1b[<32;{start + width};{row + 1}M")
        raw(f"\x1b[<0;{start + width};{row + 1}m")
        time.sleep(0.15)
        state = inspect()
        assert state["selection"] == text, state

    try:
        tmux(
            "new-session",
            "-d",
            "-s",
            "test",
            "-x",
            "120",
            "-y",
            "42",
            "-c",
            str(temp),
            shell,
        )
        wait_for(lambda: "QUOTE_TARGET alpha beta" in screen(), "synthetic transcript")
        wait_for(lambda: inspect()["mode"] == "fullscreen", "fullscreen ready")
        initial = inspect()
        assert initial["model"] == "quote-test/blocked", initial
        assert initial["api"] == "quote-test-blocked", initial
        tmux("send-keys", "-t", "test", "-l", "Existing draft")
        time.sleep(0.2)
        select("alpha beta")
        raw("\x1bq")
        time.sleep(0.2)
        state = inspect()
        expected = "Existing draft\n> alpha beta\n\n"
        assert state["draft"] == expected, state
        assert state["selection"] is None, state
        assert state["cursor"] == {"line": 3, "col": 0}, state
        tmux("send-keys", "-t", "test", "-l", "First comment")
        time.sleep(0.15)
        assert inspect()["draft"] == expected + "First comment"
        print(
            "PASS: real mouse drag → Alt+Q → quote below cursor line; cursor/comment below; selection cleared"
        )
        raw("\x1bq")
        time.sleep(0.15)
        assert inspect()["draft"] == expected + "First comment"
        print("PASS: no selection leaves existing draft unchanged")
        select("gamma delta")
        raw("\x1bq")
        time.sleep(0.2)
        state = inspect()
        expected += "First comment\n> gamma delta\n\n"
        assert state["draft"] == expected, state
        assert state["cursor"] == {"line": 6, "col": 0}, state
        assert state["modelCalls"] == 0, state
        (OUTPUT / "fullscreen.txt").write_text(
            screen() + "\n" + json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        )
        print(
            "PASS: multiple quote/comment pairs; zero model requests; isolated built-in fullscreen UI"
        )
        # Programmatic setEditorText must remain a single undo step.
        raw("\x1f")  # Ctrl+_ (default undo)
        time.sleep(0.15)
        state = inspect()
        assert state["draft"] == "Existing draft\n> alpha beta\n\nFirst comment", (
            state
        )
        print("PASS: single undo restores pre-quote draft")
        tmux("resize-window", "-t", "test", "-x", "80", "-y", "34")
        time.sleep(0.3)
        select("Привет 世界")
        previous = inspect()["draft"]
        raw("\x1bq")
        time.sleep(0.15)
        state = inspect()
        assert state["draft"] == previous + "\n> Привет 世界\n\n", state
        print("PASS: 80-column resize; Cyrillic/CJK cell-aware mouse selection")
        # Multi-line selection, including blank row and rendered transcript indentation.
        lines = screen().splitlines()
        start_row = next(
            i
            for i, line in enumerate(lines)
            if "alpha beta" in line and "QUOTE_TARGET" in line
        )
        end_row = next(
            i for i, line in enumerate(lines) if "SECOND_TARGET gamma delta" in line
        )
        start_col = lines[start_row].index("alpha beta")
        end_col = lines[end_row].index("gamma delta") + len("gamma delta")
        raw(f"\x1b[<0;{start_col + 1};{start_row + 1}M")
        raw(f"\x1b[<32;{end_col};{end_row + 1}M")
        raw(f"\x1b[<0;{end_col};{end_row + 1}m")
        time.sleep(0.15)
        before = inspect()
        assert before["selection"].startswith("alpha beta\n"), before
        assert before["selection"].endswith("gamma delta"), before
        quoted = "\n".join(
            "> " + line if line else ">" for line in before["selection"].split("\n")
        )
        raw("\x1bq")
        time.sleep(0.15)
        state = inspect()
        assert state["draft"] == before["draft"] + quoted + "\n\n", state
        assert state["modelCalls"] == 0, state
        (OUTPUT / "fullscreen.txt").write_text(
            screen() + "\n" + json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        )
        print(
            "PASS: real multiline mouse selection; quote lines/blank rows preserved; zero model requests"
        )
        # Quoting from scrolled-up transcript must keep the viewport in place, so
        # another passage from the same area can be selected without re-scrolling.
        raw("\x1bf")
        wait_for(lambda: "FILLER_119" in screen(), "transcript filler at bottom")
        assert "SCROLL_TARGET epsilon zeta" not in screen()
        for _ in range(40):
            if "SCROLL_TARGET epsilon zeta" in screen():
                break
            raw("\x1b[5~")  # PageUp
            time.sleep(0.1)
        assert "SCROLL_TARGET epsilon zeta" in screen(), screen()
        assert "FILLER_119" not in screen()
        select("epsilon zeta")
        before = inspect()
        assert before["following"] is False, before
        raw("\x1bq")
        time.sleep(0.2)
        state = inspect()
        assert state["draft"] == before["draft"] + "> epsilon zeta\n\n", state
        assert state["scrollTop"] == before["scrollTop"], (before, state)
        assert state["following"] is False, state
        assert "SCROLL_TARGET epsilon zeta" in screen(), screen()
        assert "FILLER_119" not in screen()
        select("SCROLL_TARGET")
        raw("\x1bq")
        time.sleep(0.2)
        state = inspect()
        assert state["draft"].endswith("> epsilon zeta\n\n> SCROLL_TARGET\n\n"), state
        assert state["scrollTop"] == before["scrollTop"], (before, state)
        assert state["modelCalls"] == 0, state
        print("PASS: quoting while scrolled up keeps viewport; second passage quoted without re-scrolling")
        tmux("send-keys", "-t", "test", "C-End")
        wait_for(lambda: inspect()["following"] is True, "viewport back at bottom")
        # Cursor in middle of draft: quote goes below cursor line, rest of draft stays below reply line.
        before = inspect()
        for _ in range(before["cursor"]["line"]):
            raw("\x1b[A")  # Up to first draft line ("Existing draft")
            time.sleep(0.05)
        time.sleep(0.15)
        assert inspect()["cursor"]["line"] == 0, inspect()
        select("FILLER_119")
        raw("\x1bq")
        time.sleep(0.2)
        state = inspect()
        rest = before["draft"].split("\n", 1)[1]
        assert state["draft"] == "Existing draft\n> FILLER_119\n\n\n" + rest, state
        assert state["cursor"] == {"line": 3, "col": 0}, state
        tmux("send-keys", "-t", "test", "-l", "Mid reply")
        time.sleep(0.15)
        assert inspect()["draft"] == "Existing draft\n> FILLER_119\n\nMid reply\n" + rest
        print("PASS: cursor mid-draft → quote below cursor line; gap; reply line; rest of draft kept below")
        # Verify the safety mechanism itself, not merely the zero-call happy path.
        raw("\x1bz")
        tmux("send-keys", "-t", "test", "Enter")
        wait_for(lambda: "QUOTE_TEST_TRANSPORT_BLOCKED" in screen(), "blocked transport tripwire")
        state = inspect()
        assert state["modelCalls"] == 1, state
        assert state["model"] == "quote-test/blocked", state
        wait_for(lambda: inspect()["idle"], "blocked request settled")
        print("PASS: intentional submission hits only in-process blocked transport; no network/model request")
    finally:
        tmux("kill-server", check=False)
