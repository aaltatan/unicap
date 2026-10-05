/**
 * Tables remember where you left them: filters, search, sorting and page.
 *
 * A page holding `[data-remember-url]` saves its address (HTMX keeps the applied filters in
 * it, `hx-push-url`) whenever it changes. A plain link back to that page (the sidebar,
 * "cancel", ...) then opens it as it was left. Links marked `data-url-reset` open it fresh,
 * and the fresh, empty state is what is remembered from then on.
 *
 * Kept per browser tab (sessionStorage), under an "unicap:" prefix.
 */

const PREFIX = "unicap:url:";

function backend() {
  try {
    return window.sessionStorage;
  } catch {
    return null; // storage disabled: pages simply open fresh
  }
}

function save() {
  if (!document.querySelector("[data-remember-url]")) return;

  backend()?.setItem(PREFIX + window.location.pathname, window.location.search);
}

function saved(path) {
  return backend()?.getItem(PREFIX + path) ?? "";
}

/** Point a plain link to a remembered page at its last address, just before it is followed. */
function restore(event) {
  const link = event.target.closest?.("a[href]");

  if (!link || event.defaultPrevented || event.button !== 0) return;
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  if (link.target || link.hasAttribute("download") || link.hasAttribute("data-url-reset")) return;

  const url = new URL(link.href, window.location.href);

  if (url.origin !== window.location.origin || url.search || url.hash) return;

  const search = saved(url.pathname);

  if (search) link.href = url.pathname + search;
}

export function rememberPageState() {
  save();

  document.addEventListener("htmx:pushedIntoHistory", save);
  document.addEventListener("htmx:replacedInHistory", save);
  document.addEventListener("click", restore);
}
