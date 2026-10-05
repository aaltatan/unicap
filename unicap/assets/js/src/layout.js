/**
 * Page chrome: the navigation sidebar (start side), the filters sidebar (end side),
 * the modal and the theme. Purely visual state; nothing here decides anything.
 */

import { storage } from "./storage";

const DARK_QUERY = window.matchMedia("(prefers-color-scheme: dark)");

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

    closeModal() {
      this.modalOpen = false;
      window.setTimeout(() => {
        const container = document.getElementById("modal-container");
        if (container && !this.modalOpen) container.innerHTML = "";
      }, 200);
    },
  };
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
