/** Quote Pi's active fullscreen selection. No clipboard, subprocesses, or model calls. */
import { VERSION, type ExtensionAPI, type ExtensionContext } from "@earendil-works/pi-coding-agent";

export const REVIEWED_PI_VERSION = "1.0.3";
export const SHORTCUT = "alt+q";
const BRIDGE_WIDGET = "local-quote-selection:renderer-bridge";

type SelectionRenderer = {
  mode: string;
  getActiveSelectionText(): string | undefined;
  clearTextSelection(): void;
  scrollToBottom(): void;
  requestRender(): void;
  hasOverlay(): boolean;
};

export function formatQuote(text: string): string {
  const normalized = text.replace(/\r\n?/g, "\n").replace(/^\n+|\n+$/g, "");
  if (!normalized.trim()) return "";
  // Preserve indentation, code fences, and Unicode; Pi already strips terminal escapes.
  return normalized.split("\n").map((line) => line.length ? `> ${line}` : ">").join("\n");
}

export function appendQuote(draft: string, quote: string): string {
  const separator = !draft || draft.endsWith("\n\n") ? "" : draft.endsWith("\n") ? "\n" : "\n\n";
  return `${draft}${separator}${quote}\n\n`;
}

function getRenderer(ctx: ExtensionContext): SelectionRenderer {
  let renderer: unknown;
  // A synchronous, zero-row widget factory receives Pi's live renderer reference.
  // Remove immediately: no persistent widget, editor replacement, or stale mode/session ref.
  try {
    ctx.ui.setWidget(BRIDGE_WIDGET, (tui) => {
      renderer = tui;
      return { render: () => [], invalidate() {} };
    }, { placement: "belowEditor" });
  } finally {
    ctx.ui.setWidget(BRIDGE_WIDGET, undefined);
  }
  const candidate = renderer as Partial<SelectionRenderer> | undefined;
  if (candidate?.mode !== "fullscreen") {
    throw new Error("Quote selection needs Pi fullscreen mode (normal mouse drag, not Shift+drag).");
  }
  for (const method of ["getActiveSelectionText", "clearTextSelection", "scrollToBottom", "requestRender", "hasOverlay"] as const) {
    if (typeof candidate[method] !== "function") {
      throw new Error(`Quote selection unavailable: Pi renderer API changed (${method}).`);
    }
  }
  return candidate as SelectionRenderer;
}

export function quoteSelection(ctx: ExtensionContext, version = VERSION): void {
  if (!ctx.hasUI || ctx.mode !== "tui") return;
  try {
    // Private APIs: refuse unreviewed hosts rather than guess or quote stale clipboard data.
    if (version !== REVIEWED_PI_VERSION) {
      throw new Error(`Quote selection supports reviewed Pi ${REVIEWED_PI_VERSION}; found ${version}. Review compatibility before enabling.`);
    }
    const renderer = getRenderer(ctx);
    if (renderer.hasOverlay()) {
      throw new Error("Close Pi dialog before quoting transcript selection.");
    }
    const selected = renderer.getActiveSelectionText();
    if (selected !== undefined && typeof selected !== "string") {
      throw new Error("Quote selection unavailable: Pi returned invalid selection data.");
    }
    const quote = selected === undefined ? "" : formatQuote(selected);
    if (!quote) {
      throw new Error("Select transcript text with mouse, then press Alt+Q.");
    }
    // setEditorText is undoable, expands existing paste markers, and moves cursor to end.
    ctx.ui.setEditorText(appendQuote(ctx.ui.getEditorText(), quote));
    renderer.clearTextSelection();
    renderer.scrollToBottom();
    renderer.requestRender();
  } catch (error) {
    ctx.ui.notify(error instanceof Error ? error.message : String(error), "warning");
  }
}

export default function (pi: ExtensionAPI): void {
  pi.registerShortcut(SHORTCUT, {
    description: "Quote selected fullscreen text into prompt",
    handler: async (ctx) => quoteSelection(ctx),
  });
  pi.registerCommand("quote-selection", {
    description: "Quote active fullscreen selection into prompt (Alt+Q)",
    handler: async (_args, ctx) => quoteSelection(ctx),
  });
}
