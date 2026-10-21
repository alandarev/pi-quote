import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import path from "node:path";
import { getPackageDir } from "@earendil-works/pi-coding-agent";
import extension, { appendQuote, formatQuote, quoteSelection, SHORTCUT } from "../src/index.ts";

function fixture(selected = "Selected text") {
  const calls = [];
  let draft = "Existing draft";
  const renderer = {
    mode: "fullscreen",
    getActiveSelectionText() { calls.push("read-selection"); return selected; },
    clearTextSelection() { calls.push("clear"); selected = undefined; },
    requestRender() { calls.push("render"); },
    hasOverlay() { return false; },
  };
  const ctx = {
    mode: "tui", hasUI: true,
    ui: {
      setWidget(key, factory, options) {
        assert.equal(key, "local-quote-selection:renderer-bridge");
        if (factory) {
          calls.push("mount");
          assert.equal(options.placement, "belowEditor");
          const component = factory(renderer);
          assert.deepEqual(component.render(80), []);
          component.invalidate();
        } else calls.push("unmount");
      },
      getEditorText() { return draft; },
      setEditorText(text) { calls.push("write-draft"); draft = text; },
      notify(message, type) { calls.push({ message, type }); },
    },
  };
  return { ctx, renderer, calls, get draft() { return draft; } };
}

for (const [name, text, expected] of [
  ["single line", "hello", "> hello"],
  ["multiline and empty lines", "one\n\ntwo", "> one\n>\n> two"],
  ["CRLF and CR", "one\r\ntwo\rthree", "> one\n> two\n> three"],
  ["outer blank lines", "\n\nhello\n", "> hello"],
  ["code indentation", "    first\n  second", ">     first\n>   second"],
  ["nested quotes and fences", "> nested\n```ts\nhi\n```", "> > nested\n> ```ts\n> hi\n> ```"],
  ["Unicode", "Привет 👩🏽‍💻 世界", "> Привет 👩🏽‍💻 世界"],
  ["empty", "", ""],
  ["whitespace", " \n\t\n ", ""],
]) test(`format: ${name}`, () => assert.equal(formatQuote(text), expected));

for (const [draft, expected] of [
  ["", "> quote\n\n"],
  ["draft", "draft\n\n> quote\n\n"],
  ["draft\n", "draft\n\n> quote\n\n"],
  ["draft\n\n", "draft\n\n> quote\n\n"],
  ["draft\n\n\n", "draft\n\n\n> quote\n\n"],
]) test(`append preserves draft ${JSON.stringify(draft)}`, () => assert.equal(appendQuote(draft, "> quote"), expected));

test("quotes selection, clears it, keeps scroll position, leaves comment line", () => {
  const f = fixture("one\ntwo");
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft\n\n> one\n> two\n\n");
  assert.deepEqual(f.calls, ["mount", "unmount", "read-selection", "write-draft", "clear", "render"]);
});

test("no selection preserves draft; repeat shortcut never reuses stale selection", () => {
  const f = fixture();
  quoteSelection(f.ctx);
  const before = f.draft;
  quoteSelection(f.ctx);
  assert.equal(f.draft, before);
  assert.match(f.calls.at(-1).message, /Select transcript text/);
});

for (const selected of [undefined, "", " \n ", 42]) test(`invalid/empty selection ${JSON.stringify(selected)} does not edit`, () => {
  const f = fixture(selected);
  // fixture's default argument intentionally gives a real selection for undefined.
  if (selected === undefined) f.renderer.getActiveSelectionText = () => undefined;
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft");
  assert.equal(f.calls.includes("clear"), false);
  assert.equal(f.calls.at(-1).type, "warning");
});

for (const mode of ["rpc", "json", "print"]) test(`${mode} inert, even when RPC reports UI`, () => {
  const f = fixture(); f.ctx.mode = mode;
  quoteSelection(f.ctx);
  assert.deepEqual(f.calls, []);
});

test("no UI inert", () => {
  const f = fixture(); f.ctx.hasUI = false;
  quoteSelection(f.ctx); assert.deepEqual(f.calls, []);
});

test("unreviewed host fails closed before touching UI", () => {
  const f = fixture(); quoteSelection(f.ctx, "999.0.0");
  assert.equal(f.calls.length, 1);
  assert.match(f.calls[0].message, /Review compatibility/);
});

test("regular mode rejected without editing", () => {
  const f = fixture(); f.renderer.mode = "regular";
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft");
  assert.match(f.calls.at(-1).message, /fullscreen mode/);
});

test("missing private method rejected", () => {
  const f = fixture(); delete f.renderer.getActiveSelectionText;
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft");
  assert.match(f.calls.at(-1).message, /API changed/);
});

test("overlay blocks quoting", () => {
  const f = fixture(); f.renderer.hasOverlay = () => true;
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft");
  assert.match(f.calls.at(-1).message, /Close Pi dialog/);
});

test("getter failure preserves draft and bridge removed", () => {
  const f = fixture(); f.renderer.getActiveSelectionText = () => { throw new Error("fixture error"); };
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft");
  assert.deepEqual(f.calls.slice(0, 2), ["mount", "unmount"]);
  assert.equal(f.calls.at(-1).message, "fixture error");
});

test("failed editor write never clears selection", () => {
  const f = fixture(); f.ctx.ui.setEditorText = () => { throw new Error("write failed"); };
  quoteSelection(f.ctx);
  assert.equal(f.calls.includes("clear"), false);
});

test("each invocation gets current renderer, no stale session/mode capture", () => {
  const f = fixture("first"); quoteSelection(f.ctx);
  f.renderer.getActiveSelectionText = () => "second";
  quoteSelection(f.ctx);
  assert.equal(f.draft, "Existing draft\n\n> first\n\n> second\n\n");
});

test("registration has one shortcut and one command, no tools/events", () => {
  const shortcuts = [], commands = [];
  extension({ registerShortcut: (...args) => shortcuts.push(args), registerCommand: (...args) => commands.push(args) });
  assert.equal(shortcuts.length, 1); assert.equal(commands.length, 1);
  assert.equal(shortcuts[0][0], SHORTCUT);
  const f = fixture(); shortcuts[0][1].handler(f.ctx);
  assert.match(f.draft, /> Selected text/);
});

test("Pi actual loader loads candidate without warnings", async () => {
  const { loadExtensions } = await import(pathToFileURL(path.join(getPackageDir(), "dist/core/extensions/loader.js")));
  const source = path.join(import.meta.dirname, "../src/index.ts");
  const loaded = await loadExtensions([source], import.meta.dirname);
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  assert.equal(loaded.extensions[0].tools.size, 0);
  assert.equal(loaded.extensions[0].commands.has("quote-selection"), true);
});
