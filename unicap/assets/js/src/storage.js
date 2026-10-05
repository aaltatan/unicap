/**
 * The storage every `$persist` uses (`.using(storage)`): localStorage under an "unicap:" prefix,
 * since other apps served from the same origin (localhost:8000) share localStorage, and a
 * value that is not JSON reads as missing (Alpine's persist would throw on JSON.parse).
 */

const PREFIX = "unicap:";

function backend() {
  try {
    return window.localStorage;
  } catch {
    return null; // storage disabled: everything reads as missing, nothing is kept
  }
}

export const storage = {
  getItem(key) {
    const value = backend()?.getItem(PREFIX + key) ?? null;

    if (value === null) return null;

    try {
      JSON.parse(value);
      return value;
    } catch {
      backend()?.removeItem(PREFIX + key);
      return null;
    }
  },

  setItem(key, value) {
    backend()?.setItem(PREFIX + key, value);
  },

  removeItem(key) {
    backend()?.removeItem(PREFIX + key);
  },
};
