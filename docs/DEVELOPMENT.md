# Compatibility and tests

## Current support

Version 0.1.1 supports **Pi 1.0.3**, in its built-in fullscreen UI. Open TUI is not required. Standard scrollback mode, terminal-owned selections, RPC, JSON, and print mode do not provide this selection workflow.

The extension uses public editor/widget APIs and private fullscreen selection methods. A synchronous, zero-row widget factory obtains Pi's live renderer reference; the widget is removed immediately. The action reads `getActiveSelectionText()`, appends a blockquote through `setEditorText()`, clears selection through `clearTextSelection()`, and keeps the transcript scroll position (the editor stays visible in Pi's fixed input dock), so several passages can be quoted from one place. It does not replace the editor, header, or footer, leave a persistent widget, or patch Pi's source.

The version guard and method-shape checks are intentional. On an unsupported version, the shortcut warns and does not alter the draft. Do not relax guards based only on a matching method name: selection/editor behavior must also be tested.

## Tests

```bash
npm ci
npm run check
npm run test:e2e
npm pack --dry-run
```

Unit tests cover quote formatting, newline separation, code indentation, Unicode, preserving draft, repeated quotes, empty/stale selection, unsupported modes/versions, missing APIs, overlays, failures, and actual Pi extension loading.

The fullscreen test runs a separate tmux server with user configuration disabled, plus a Pi process with isolated configuration, a synthetic transcript, and no real credentials. Its selected test model uses a unique in-process API whose transport always throws before any network request; it cannot fall through to a real provider. It drives real SGR mouse drags and Alt+Q, then checks editor text, cursor placement, repeated comments, single-step undo, narrow-window resizing, Cyrillic/CJK selection, and multiline quotes. The quote workflow must make zero transport attempts. Finally, an intentional submission verifies the blocking transport is actually selected and rejects the request. No real model call is made. Evidence under `test/e2e/out/` is ignored by Git and excluded from npm.

A release should pass against the package's pinned development Pi and, for any newly supported host, that exact installed host. The existing user's unrelated Pi configuration should not be modified by tests.

Development overrides keep Pi's internal package family at 1.0.3. Its transitive semver ranges otherwise resolve to newer, incompatible packages (for example, codemode 1.3.0 no longer exports a symbol expected by Pi 1.0.3). These overrides are for this repository's test host only; consumers use their own Pi host, and the extension ships no runtime dependencies.

## Reviewing a new Pi version

1. Inspect fullscreen selection extraction/clearing, the renderer reference, the synchronous widget factory, and editor text/undo behavior.
2. Run unit and fullscreen tests against the new host without replacing any working user installation.
3. Add support only after passing those checks. Update source guard, development dependency, README, and release notes together.
4. Release a new version; never silently rewrite an already published version.
