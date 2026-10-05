/**
 * Keyboard shortcuts on any keyboard layout.
 *
 * On an Arabic layout a key types its own letter (Alt+س, not Alt+S), so the templates'
 * `@keydown.alt.s`, `@keydown.ctrl.k`, `@keydown.slash`, ... never match. The key's position
 * (`event.code`, else the Arabic letter itself) says which Latin key it is: the shortcut is
 * replayed as that key, so every shortcut works the same whatever language the keyboard (or
 * the site) is in.
 */

const POSITIONS = { Slash: "/" };

// the Arabic layout's letters by their Latin key, for keyboards that report no position
const ARABIC = Object.fromEntries(
  [..."ضصثقفغعهخحشسيبلاتنمئءؤرىةظ"].map((letter, index) => [letter, "qwertyuiopasdfghjklzxcvnm/"[index]]),
);

const EDITABLE = ["INPUT", "TEXTAREA", "SELECT"];

/** The Latin key at the pressed key's position: "s" for KeyS, "/" for Slash (else null). */
function latinKey(event) {
  const letter = /^Key([A-Z])$/.exec(event.code);

  if (letter) {
    return letter[1].toLowerCase();
  }

  return POSITIONS[event.code] ?? ARABIC[event.key] ?? null;
}

/** A shortcut, not typing: a letter with Ctrl / Alt / Cmd, or "/" outside a field. */
function isShortcut(event, key) {
  const modified = event.ctrlKey || event.altKey || event.metaKey;

  if (key.length === 1 && key !== "/") {
    return modified;
  }

  const target = event.target;

  return !modified && !EDITABLE.includes(target.tagName) && !target.isContentEditable;
}

/** The layout already typed a Latin character (QWERTY, AZERTY, Dvorak): nothing to replay. */
function isLatin(event) {
  return event.key.length === 1 && event.key.charCodeAt(0) < 128;
}

export function shortcutsOnAnyLayout() {
  window.addEventListener(
    "keydown",
    (event) => {
      if (!event.isTrusted || event.isComposing || isLatin(event)) {
        return;
      }

      const key = latinKey(event);

      if (!key || !isShortcut(event, key)) {
        return;
      }

      const replay = new KeyboardEvent("keydown", {
        key,
        code: event.code,
        ctrlKey: event.ctrlKey,
        altKey: event.altKey,
        shiftKey: event.shiftKey,
        metaKey: event.metaKey,
        bubbles: true,
        cancelable: true,
      });

      // a handler that took the shortcut (`.prevent`) also stops the letter being typed
      if (!event.target.dispatchEvent(replay)) {
        event.preventDefault();
      }
    },
    true,
  );
}
