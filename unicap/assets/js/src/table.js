import { storage } from "./storage";

/**
 * Tables: which columns show and in what order (dragged in the "columns" menu,
 * remembered per table), and the rows checked for bulk actions.
 *
 * Every header and cell carries `data-col`; columns without it (the checkbox, the index)
 * always stay first, and `data-pin="end"` ones (the row actions) last. The table is re-rendered by HTMX, so the layout is re-applied
 * after every swap.
 */
export function tableColumns(key, columns) {
  return {
    columns, // [{ key, label }] in the server's order
    order: this.$persist(columns.map((column) => column.key)).as(`columns-${key}`).using(storage),
    hidden: this.$persist([]).as(`hidden-columns-${key}`).using(storage),

    init() {
      // columns added since the order was saved go last
      const known = new Set(this.order);
      this.order = [
        ...this.order.filter((column) => this.columns.some((c) => c.key === column)),
        ...this.columns.map((c) => c.key).filter((column) => !known.has(column)),
      ];

      this.$nextTick(() => this.apply());

      document.body.addEventListener("htmx:afterSettle", () => this.apply());
    },

    isHidden(column) {
      return this.hidden.includes(column);
    },

    toggleColumn(column) {
      this.hidden = this.isHidden(column)
        ? this.hidden.filter((c) => c !== column)
        : [...this.hidden, column];
      this.apply();
    },

    /** After a drop in the "columns" menu: its items' order is the columns' order. */
    readMenuOrder() {
      this.order = [...document.getElementById("columns-menu").children].map((item) => item.dataset.col);
      this.apply();
    },

    resetColumns() {
      this.order = this.columns.map((c) => c.key);
      this.hidden = [];
      this.apply();
    },

    apply() {
      const menu = document.getElementById("columns-menu");
      if (menu) {
        const items = Object.fromEntries([...menu.children].map((item) => [item.dataset.col, item]));
        this.order.forEach((column) => items[column] && menu.appendChild(items[column]));
      }

      const table = document.querySelector("#table table");
      if (!table) return;

      // phones show each row as a card: every cell carries its column's label
      const labels = Object.fromEntries(
        this.columns.map((c) => [c.key, c.label.charAt(0).toUpperCase() + c.label.slice(1)]),
      );
      table.querySelectorAll("tbody td[data-col]").forEach((cell) => {
        cell.dataset.label = labels[cell.dataset.col] || "";
      });

      for (const row of table.rows) {
        const cells = [...row.cells];
        const byColumn = Object.fromEntries(
          cells.filter((cell) => cell.dataset.col).map((cell) => [cell.dataset.col, cell]),
        );

        this.order.forEach((column) => {
          const cell = byColumn[column];
          if (!cell) return;
          row.appendChild(cell);
          cell.classList.toggle("hidden", this.isHidden(column));
        });

        cells.filter((cell) => cell.dataset.pin === "end").forEach((cell) => row.appendChild(cell));
      }
    },
  };
}

/** Checked rows: "select all", the count on the bulk actions button. */
export function tableSelection() {
  return {
    selected: 0,

    init() {
      this.count();
      document.body.addEventListener("htmx:afterSettle", () => this.count());
    },

    boxes() {
      return [...document.querySelectorAll("#table input[name='ids']")];
    },

    count() {
      this.selected = this.boxes().filter((box) => box.checked).length;
    },

    toggleAll(checked) {
      this.boxes().forEach((box) => (box.checked = checked));
      this.count();
    },

    /** Phones have no checkboxes and no "⋮": tapping a row card opens its details. */
    openOnPhone(event, url) {
      if (!window.matchMedia(PHONE).matches) return;
      if (event.target.closest(INTERACTIVE)) return;

      window.htmx.ajax("GET", url, { target: "#modal-container", swap: "innerHTML" });
    },

    /** A right click on a row opens its "⋮" menu where the pointer is (Shift: the browser's). */
    openRowMenu(event) {
      if (event.shiftKey || window.matchMedia(PHONE).matches) return;
      if (event.target.closest("input, select, textarea")) return;

      const menu = event.currentTarget.querySelector("[data-row-menu]");
      if (!menu) return;

      event.preventDefault();
      menu.dispatchEvent(
        new CustomEvent("open-at", { detail: { x: event.clientX, y: event.clientY } }),
      );
    },

    /** A double click on a row (not on what it holds to click) opens its edit form. */
    editRow(event, url) {
      if (event.target.closest(INTERACTIVE)) return;

      window.getSelection()?.removeAllRanges(); // the double click selected a word
      window.htmx.ajax("GET", url, { target: "#modal-container", swap: "innerHTML" });
    },
  };
}

/** What a row holds that has its own click: clicking it is not clicking the row. */
const INTERACTIVE = "a, button, input, select, label, textarea, [role='menu']";

/** Keep in sync with the `.data-table.cards` media query in main.css (Tailwind's `sm`). */
const PHONE = "(max-width: 639px)";

/**
 * The export link of the table as it is now: filters, search and sorting are applied with
 * HTMX, which keeps them in the address bar (`hx-push-url`), so they are read on click.
 * Every filtered row is exported, so the page number is dropped.
 */
export function exportUrl(format) {
  const params = new URLSearchParams(window.location.search);
  params.delete("page");
  params.set("export", format);
  return `${window.location.pathname}?${params}`;
}

/**
 * A row's actions under a "⋮" button. The menu is `position: fixed`, placed from the
 * button, so the table's scrolling box cannot clip it: below the button (above when there
 * is no room), its end edge on the button's (right-to-left aware). Scrolling closes it.
 */
export function rowMenu() {
  return {
    open: false,
    position: "",

    toggle() {
      if (this.open) this.close();
      else this.show();
    },

    /** Under the "⋮" button; or, with a `point` (a right click on the row), where it is. */
    show(point = null) {
      this.open = true;
      this.position = "";

      this.$nextTick(() => {
        const menu = this.$refs.menu;
        const { offsetWidth: width, offsetHeight: height } = menu;
        const rtl = document.documentElement.dir === "rtl";

        let top;
        let start;

        if (point) {
          top = point.y + height > window.innerHeight ? point.y - height : point.y;
          start = rtl ? point.x - width : point.x;
        } else {
          const button = this.$refs.button.getBoundingClientRect();
          const below = button.bottom + 4;

          top = below + height > window.innerHeight ? button.top - 4 - height : below;
          start = rtl ? button.left : button.right - width;
        }

        const left = Math.min(Math.max(4, start), window.innerWidth - width - 4);

        this.position = `top: ${Math.max(4, top)}px; left: ${left}px`;
      });

      const close = () => this.close();
      window.addEventListener("scroll", close, { capture: true, once: true });
      window.addEventListener("resize", close, { once: true });
    },

    close() {
      this.open = false;
      this.position = "";
    },
  };
}
