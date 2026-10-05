/**
 * Drag and drop without selecting text. The sortables use the pointer fallback
 * (`forceFallback: true`), so the browser starts a text selection on the pointer press
 * and stretches it over the page while dragging; Sortable only stops it once the drag has
 * begun. Selection is off from the press on a drag start (a handle, or a board card,
 * which drags as a whole) until the pointer is released; the content stays selectable.
 */

const DRAG_START = "[x-sort\\:handle], .widget-handle, .lane-handle, .drag-handle, .board-card";

const CLASS = "no-select";

export function preventSelectionWhileDragging() {
  const root = document.documentElement;
  const release = () => root.classList.remove(CLASS);

  document.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || !event.target.closest?.(DRAG_START)) return;

    window.getSelection()?.removeAllRanges();
    root.classList.add(CLASS);
  });

  document.addEventListener("pointerup", release);
  document.addEventListener("pointercancel", release);
  window.addEventListener("blur", release);
}
