/**
 * Page chrome: the navigation sidebar (start side), the filters sidebar (end side),
 * the modal and the theme. Purely visual state; nothing here decides anything.
 */

import { storage } from "./storage";

const DARK_QUERY = window.matchMedia("(prefers-color-scheme: dark)");

// what a modal focuses when it shows: the field it marks (`autofocus`), else its first one
// (a searched select's own <select> is hidden behind its text input, which is the field)
const MODAL_FIELDS = "input:not([type=hidden]), select, textarea";
const MODAL_FOCUS_RETRIES = [60, 180, 400]; // ms: while it fades in, or something took the focus

/** Theme store: "light", "dark" or "system" (follows the operating system). */
export function themeStore(Alpine) {
  return {
    mode: Alpine.$persist("system").as("theme").using(storage),

    init() {
      this.apply();
      DARK_QUERY.addEventListener("change", () => this.apply());
    },

    get dark() {
      return this.mode === "dark" || (this.mode === "system" && DARK_QUERY.matches);
    },

    set(mode) {
      this.mode = mode;
      this.apply();
    },

    apply() {
      document.documentElement.classList.toggle("dark", this.dark);
      document.documentElement.style.colorScheme = this.dark ? "dark" : "light";
    },
  };
}

export function layout() {
  return {
    // navigation sidebar: collapsed to icons on large screens, off-canvas on small ones
    navCollapsed: this.$persist(false).as("nav-collapsed").using(storage),
    navOpen: false,

    // filters sidebar: pinned beside the content on large screens, else an overlay
    filtersOpen: false,
    filtersPinned: this.$persist(false).as("filters-pinned").using(storage),

    modalOpen: false,

    init() {
      document.body.addEventListener("htmx:afterSwap", (event) => {
        if (event.detail.target.id === "modal-container" && event.detail.target.innerHTML.trim()) {
          this.modalOpen = true;
          this.focusModal(event.detail.target);
        }
      });

      document.body.addEventListener("close-modal", () => this.closeModal());

      document.body.addEventListener("open-modal", (event) => {
        window.htmx.ajax("GET", event.detail.value, { target: "#modal-container", swap: "innerHTML" });
      });

      document.body.addEventListener("htmx:beforeHistorySave", () => {
        this.modalOpen = false;
        document.getElementById("modal-container").innerHTML = "";
      });

      // a request that failed swaps nothing: say so, in the words the server wrote
      document.body.addEventListener("htmx:responseError", (event) => errorToast(event.detail.xhr.status));
      document.body.addEventListener("htmx:sendError", () => errorToast("offline"));
      document.body.addEventListener("htmx:timeout", () => errorToast("offline"));
    },

    toggleNav() {
      if (window.matchMedia("(min-width: 1024px)").matches) {
        this.navCollapsed = !this.navCollapsed;
      } else {
        this.navOpen = !this.navOpen;
      }
    },

    toggleFilters() {
      this.filtersOpen = !this.filtersOpen;
    },

    get filtersBeside() {
      return this.filtersOpen && this.filtersPinned;
    },

    // a modal just drawn: focus its first field, else its close button. What the modal
    // focused itself (a confirm button) is left alone; so is a focus the user moved since.
    focusModal(container) {
      const drawn = container.firstElementChild;

      // from the first key or press on, the focus is the user's: nothing takes it back
      let touched = false;
      const touch = () => (touched = true);
      const once = { capture: true, once: true };
      container.addEventListener("keydown", touch, once);
      container.addEventListener("pointerdown", touch, once);

      const focus = () => {
        if (touched || !this.modalOpen || container.firstElementChild !== drawn) return;
        if (container.contains(document.activeElement)) return;

        modalFocusTarget(container)?.focus({ preventScroll: true });
      };

      this.$nextTick(focus);
      MODAL_FOCUS_RETRIES.forEach((delay) => window.setTimeout(focus, delay));
    },

    // empty the filters form (and, with `search`, the search box): the link clicked then
    // fetches the table without them, so the page is not reloaded
    clearFilters({ search = false } = {}) {
      const form = document.getElementById("filters-form");
      if (!form) return;

      form.querySelectorAll("input, select, textarea").forEach((control) => {
        if (control.type === "checkbox" || control.type === "radio") control.checked = false;
        else if (control.tagName === "SELECT") control.selectedIndex = control.multiple ? -1 : 0;
        else control.value = "";

        // widgets drawn over a control (a searched select, a list's own search) follow it
        control.dispatchEvent(new Event("input", { bubbles: true }));
        control.dispatchEvent(new Event("change", { bubbles: true }));
      });

      if (search) {
        document.querySelectorAll("input[name='q'][form='filters-form']").forEach((input) => {
          input.value = "";
        });
      }
    },

    closeModal() {
      this.modalOpen = false;
      window.setTimeout(() => {
        const container = document.getElementById("modal-container");
        if (container && !this.modalOpen) container.innerHTML = "";
      }, 200);
    },
  };
}

/** The element a modal focuses: marked `autofocus`, else its first field, else its close button. */
function modalFocusTarget(container) {
  const usable = (element) =>
    !element.disabled &&
    !element.closest(".sr-only") && // a searched select's native <select>
    element.getClientRects().length > 0;

  const marked = [...container.querySelectorAll("[autofocus]")].find(usable);
  const field = [...container.querySelectorAll(MODAL_FIELDS)].find(usable);

  return marked || field || container.querySelector("[data-modal-close]");
}

/** Show the toast the layout holds for a failed request (`<template data-error-toast>`). */
function errorToast(status) {
  const toasts = document.getElementById("messages");
  const template =
    document.querySelector(`template[data-error-toast="${status}"]`) ||
    document.querySelector('template[data-error-toast="error"]');

  if (toasts && template) toasts.appendChild(template.content.cloneNode(true));
}

/** A dropdown menu: open / close, closing on outside click and Escape. */
export function dropdown() {
  return {
    open: false,
    toggle() {
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
  };
}

/** A message toast that closes itself after a while (errors stay until closed). */
export function toast(level) {
  return {
    show: false,
    init() {
      this.$nextTick(() => (this.show = true));
      if (level !== "error") window.setTimeout(() => (this.show = false), 5000);
    },
  };
}

/**
 * Cards whose order the user drags (dashboard widgets), remembered per browser.
 * Each child has `data-key`; unknown keys keep their place at the end.
 */
export function persistedOrder(key) {
  return {
    order: this.$persist([]).as(`order-${key}`).using(storage),

    init() {
      this.$nextTick(() => this.restore());
    },

    restore() {
      const children = [...this.$el.children];
      const byKey = Object.fromEntries(children.map((child) => [child.dataset.key, child]));

      this.order
        .filter((itemKey) => byKey[itemKey])
        .forEach((itemKey) => this.$el.appendChild(byKey[itemKey]));

      children.filter((child) => !this.order.includes(child.dataset.key)).forEach((child) => this.$el.appendChild(child));
    },

    save() {
      this.order = [...this.$el.children].map((child) => child.dataset.key);
    },
  };
}
