# Changelog

## 0.1.3

- Work on new Pi versions without a release: the exact Pi version gate is gone. Each Alt+Q
  checks that the private fullscreen renderer methods (`getActiveSelectionText`,
  `clearTextSelection`, `requestRender`, `hasOverlay`, `getFocusedComponent`) exist; if Pi
  changed them, it warns and leaves the draft untouched. If the prompt editor lacks its cursor
  methods, the quote is appended at the end of the draft instead.
- Tested on Pi 1.0.3 and 1.4.0 (`TESTED_PI_VERSIONS`), including the real-mouse fullscreen
  harness against an isolated Pi 1.4.0 host.

## 0.1.2

- Insert the Alt+Q quote below the cursor line instead of appending at the end of the draft.

## 0.1.1

- Keep the transcript scroll position after Alt+Q.

## 0.1.0

- First release: quote fullscreen selections with Alt+Q.
