/**
 * One popup for every tooltip: whatever has a `title` shows it in a styled popup instead of
 * the browser's own (slow, unstyled, cut after a few lines).
 *
 * Templates keep writing `title="..."`. When the pointer (or the keyboard focus) reaches such
 * an element its title moves to `data-tip`, so the browser shows nothing itself, and the
 * popup shows it: lines stay lines, each in its own direction (Arabic names in an English
 * page), and a long list flows into columns. Purely visual; nothing here decides anything.
 */

const SELECTOR = "[title], [data-tip]";

const DELAY = 120; // ms before the popup shows: none while the pointer only passes over
const GAP = 8; // px between the element and its popup, and the least to the window's edges
const LINES_PER_COLUMN = 18;

let popup = null;
let shown = null;
let timer = null;

/** The element's tooltip text; its `title` is taken away so the browser shows none of its own. */
function take(element) {
  const title = element.getAttribute("title");

  if (title !== null) {
    element.removeAttribute("title");
    element.dataset.tip = title;

    // an icon button named only by its title keeps a name for screen readers
    if (title && !element.hasAttribute("aria-label") && !element.textContent.trim()) {
      element.setAttribute("aria-label", title);
    }
  }

  return (element.dataset.tip ?? "").trim();
}

function ensurePopup() {
  if (!popup) {
    popup = document.createElement("div");
    popup.className = "tooltip";
    popup.setAttribute("role", "tooltip");
    popup.hidden = true;
    document.body.appendChild(popup);
  }

  return popup;
}

/** Under the element (above it when there is no room), centered on it, inside the window. */
function place(element, tip) {
  const target = element.getBoundingClientRect();
  const size = tip.getBoundingClientRect();

  const below = target.bottom + GAP;
  const above = target.top - GAP - size.height;
  const fitsBelow = below + size.height <= window.innerHeight - GAP;

  const top = fitsBelow || above < GAP ? below : above;
  const left = target.left + target.width / 2 - size.width / 2;

  tip.style.top = `${Math.max(GAP, Math.min(top, window.innerHeight - size.height - GAP))}px`;
  tip.style.left = `${Math.max(GAP, Math.min(left, window.innerWidth - size.width - GAP))}px`;
}

function show(element) {
  const text = take(element);

  if (!text || !element.isConnected) {
    return;
  }

  const tip = ensurePopup();

  tip.textContent = text;
  tip.style.columnCount = Math.ceil(text.split("\n").length / LINES_PER_COLUMN);
  tip.style.top = "0px";
  tip.style.left = "0px";
  tip.hidden = false;

  place(element, tip);

  shown = element;
}

function hide() {
  clearTimeout(timer);
  timer = null;
  shown = null;

  if (popup) {
    popup.hidden = true;
  }
}

function enter(event) {
  const element = event.target.closest?.(SELECTOR);

  if (!element || element === shown) {
    return;
  }

  hide();
  take(element); // right away: the browser's own tooltip must never get its turn

  timer = setTimeout(() => show(element), DELAY);
}

function leave(event) {
  const element = event.target.closest?.(SELECTOR);

  // moving between an element's own children is not leaving it
  if (element && !element.contains(event.relatedTarget)) {
    hide();
  }
}

export function tooltips() {
  document.addEventListener("mouseover", enter);
  document.addEventListener("mouseout", leave);
  document.addEventListener("focusin", enter);
  document.addEventListener("focusout", hide);

  // anything that moves or replaces what is under the popup takes it away
  for (const event of ["pointerdown", "keydown", "wheel", "htmx:beforeSwap"]) {
    document.addEventListener(event, hide, { capture: true, passive: true });
  }

  window.addEventListener("scroll", hide, { capture: true, passive: true });
  window.addEventListener("blur", hide);
}
