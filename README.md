# pi-quote

Select part of Pi's answer, press **Alt+Q**, and write your reply underneath. No copying, pasting, or typing quote fences.

```text
> The cache should expire after 24 hours.

Should reads reset that timer?
```

## Install

```bash
pi install npm:pi-quote-jev
```

Or install the tagged source directly:

```bash
pi install git:github.com/alandarev/pi-quote@v0.1.1
```

Requires **Pi 1.0.3 in fullscreen mode**. This release uses an internal selection API and deliberately refuses unreviewed Pi versions. No other extension is required.

The npm name is `pi-quote-jev`; the unrelated `pi-quote` package belongs to another author.

## Use

1. Select text with a normal mouse drag inside Pi.
2. Press **Alt+Q**.
3. Type your comment below the quote. Repeat for other passages, then send when ready.

Your existing draft stays intact. Quotes go at its end, with a blank line before and after. The cursor moves below the quote, and undo restores the previous draft in one step. `/quote-selection` also works, but the shortcut saves typing.

Use Pi's selection, not terminal-native Shift+drag or tmux copy mode. If you already use the standalone `quote-selection.ts`, disable it before loading this package so the shortcut is not registered twice.

## No clipboard dependency

Selected text comes directly from Pi's fullscreen renderer. The extension never reads or writes your clipboard, simulates keys, opens a browser, calls a model, or sends your draft. Pi's own copy-on-select setting is unchanged.

You quote what Pi displays, not the original Markdown source. Visible line wraps may become newlines; rendered formatting may differ from the model's raw text.

## Development

```bash
npm ci
npm run check
npm run test:e2e  # Python 3 + tmux; synthetic fullscreen session, no model calls
```

[Publishing](https://github.com/alandarev/pi-quote/blob/master/docs/PUBLISHING.md) · [Compatibility and tests](https://github.com/alandarev/pi-quote/blob/master/docs/DEVELOPMENT.md)

MIT license.
