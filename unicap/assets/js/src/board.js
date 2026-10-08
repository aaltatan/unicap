import { matches as textMatches } from "./search-select";
import { storage } from "./storage";

/**
 * The drag-and-drop board (Alpine sort, i.e. SortableJS, between lanes).
 *
 * When a card is picked up, the server evaluates every drop it could make and returns,
 * per lane, whether the contract would be counted there and what the capacity would
 * become. While dragging, the hovered lane is outlined with that color and the hint
 * shows it; dropping posts the move and the server re-renders the board. A dock over the
 * page header repeats every lane as a drop target, so a faculty out of sight needs no
 * scrolling; full screen (the device's) lays the lanes out as columns as tall as the screen;
 * a lane's bottom edge drags its row taller or shorter (remembered per browser).
 *
 * A card's menu (a right click, or its "⋮") switches the contract's two-valued terms; a
 * double click on a faculty's lane opens its form.
 * Nothing is decided here: the colors, the texts and what a menu may switch come from the
 * domain's evaluation.
 */
const MIN_LANE_HEIGHT = 96; // px: a lane dragged shorter still shows a few cards

export function board({ previewUrl, moveUrl, toggleUrl }) {
  return {
    previews: {},
    hovered: null,
    sourceLane: null,
    hint: "",
    dragging: false,
    search: "",
    // lane -> what its own search box holds: its cards that do not match are hidden
    laneSearch: {},
    menu: null, // the card whose menu is open: its contract's terms, and where to draw it
    fullscreen: false,
    // faculty id -> the height (px) its cards were dragged to; the others keep their own
    laneHeights: this.$persist({}).as("board-lane-heights").using(storage),

    init() {
      // the browser leaves full screen on its own too (Esc, F11, another tab)
      document.addEventListener("fullscreenchange", () => {
        this.fullscreen = Boolean(document.fullscreenElement);
        if (!this.fullscreen) navigator.keyboard?.unlock?.();
      });
    },

    get sortConfig() {
      return {
        animation: 150,
        ghostClass: "opacity-40",
        // only cards are sorted: a dock target's labels are not, so a card drops anywhere on it
        draggable: ".board-card",
        // pointer events instead of native drag and drop: the same on mouse, touch and pen
        forceFallback: true,
        fallbackTolerance: 3,
        fallbackOnBody: true,
        // lanes scroll on their own: near a lane's (or the page's) edge, scroll it
        scroll: true,
        bubbleScroll: true,
        scrollSensitivity: 60,
        scrollSpeed: 14,
        onStart: (event) => this.start(event),
        onMove: (event) => this.over(event),
        onEnd: () => this.end(),
      };
    },

    start(event) {
      document.body.classList.add("sorting");
      this.closeMenu();
      this.dragging = true;
      this.previews = {};
      this.hint = "";
      this.sourceLane = event.from.dataset.lane;

      const employee = event.item.dataset.employee;

      fetch(`${previewUrl}?employee=${encodeURIComponent(employee)}`, {
        headers: { "HX-Request": "true" },
      })
        .then((response) => (response.ok ? response.json() : { lanes: {} }))
        .then((data) => {
          if (!this.dragging) return;
          this.previews = data.lanes || {};
          this.showHint();
        })
        .catch(() => {});
    },

    over(event) {
      this.hovered = event.to.dataset.lane;
      this.showHint();
      return true;
    },

    end() {
      document.body.classList.remove("sorting");
      this.dragging = false;
      this.hovered = null;
      this.previews = {};
      this.hint = "";
    },

    showHint() {
      const preview = this.previews[this.hovered];
      this.hint = preview ? preview.hint : "";
    },

    laneClass(lane) {
      if (!this.dragging || this.hovered !== lane) return "";
      const preview = this.previews[lane];
      if (!preview) return "would-unsign";
      if (preview.counted === null) return "would-unsign";
      return preview.counted ? "would-count" : "would-not-count";
    },

    drop(employee, lane) {
      if (lane === this.sourceLane) {
        // reordering inside a lane changes nothing: redraw to undo the DOM move
        document.body.dispatchEvent(new CustomEvent("refresh"));
        return;
      }

      window.htmx.ajax("POST", moveUrl, {
        target: "#board",
        swap: "outerHTML",
        values: { employee, faculty: lane === "unsigned" ? "" : lane },
        headers: { "X-CSRFToken": csrfToken() },
      });
    },

    // --- a card: its details, and its menu ---------------------------------------------

    openCard(card) {
      this.openModal(card.dataset.details);
    },

    /** A right click on a card, or its "⋮": the menu where the pointer (or the button) is. */
    openMenu(event, card) {
      if (event.shiftKey) return; // Shift + right click: the browser's own menu

      event.preventDefault();

      const data = card.dataset;
      const button = event.currentTarget.getBoundingClientRect();
      // a button pressed with the keyboard has no pointer position
      const x = event.clientX || button.left;
      const y = event.clientY || button.bottom;

      this.menu = {
        employee: data.employee,
        name: data.name,
        details: data.details,
        edit: data.edit,
        active: data.active === "1",
        locked: data.lock === "1",
        degree: data.degree,
        contractType: data.contractType,
        employmentType: data.employmentType,
        blocked: (data.blocked || "").split(" ").filter(Boolean),
        style: "visibility: hidden", // until it is measured
      };

      this.$nextTick(() => {
        if (!this.menu) return;

        const { offsetWidth: width, offsetHeight: height } = this.$refs.cardMenu;
        const rtl = document.documentElement.dir === "rtl";

        const top = y + height > window.innerHeight ? y - height : y;
        const left = Math.min(Math.max(4, rtl ? x - width : x), window.innerWidth - width - 4);

        this.menu.style = `top: ${Math.max(4, top)}px; left: ${left}px`;
      });

      window.addEventListener("scroll", () => this.closeMenu(), { capture: true, once: true });
    },

    closeMenu() {
      this.menu = null;
    },

    /** Whether the domain refuses to switch this term on the menu's contract. */
    isBlocked(field) {
      return Boolean(this.menu?.blocked.includes(field));
    },

    /** The menu's "details" or "edit". */
    openFromMenu(which) {
      this.openModal(this.menu[which]);
    },

    /** Switch one of the contract's two-valued terms; the server redraws the board. */
    switchCard(field) {
      window.htmx.ajax("POST", toggleUrl, {
        target: "#board",
        swap: "outerHTML",
        values: { employee: this.menu.employee, field },
        headers: { "X-CSRFToken": csrfToken() },
      });
    },

    // --- full screen -----------------------------------------------------------------------

    /**
     * The device's full screen, for the whole page (so modals and toasts still show), the
     * board drawn over the rest of it. Where the device has none (an iPhone), or refuses,
     * the board still takes the whole window.
     */
    toggleFullscreen() {
      if (this.fullscreen) {
        this.leaveFullscreen();
        return;
      }

      const page = document.documentElement;

      if (!page.requestFullscreen) {
        this.fullscreen = true;
        return;
      }

      page
        .requestFullscreen()
        // Esc then comes to the page first: it closes a menu or a modal before the full screen
        .then(() => navigator.keyboard?.lock?.(["Escape"])?.catch(() => {}))
        .catch(() => {
          this.fullscreen = true;
        });
    },

    leaveFullscreen() {
      if (document.fullscreenElement) document.exitFullscreen();
      else this.fullscreen = false;
    },

    // --- a lane ---------------------------------------------------------------------------

    /** Whether a card shows in its lane: every word of the lane's search is in its text. */
    laneShows(lane, card) {
      return textMatches(card.dataset.search, this.laneSearch[lane] || "");
    },

    /** A card's look: hidden by its lane's search, else faded by the board's. */
    cardClass(lane, card) {
      if (!this.laneShows(lane, card)) return "hidden";

      return this.matches(card.dataset.name) ? "" : "opacity-20";
    },

    /** A lane's count: its cards, or "shown / all" while its search hides some. */
    laneCount(lane, total) {
      if (!(this.laneSearch[lane] || "").trim()) return total;

      const cards = document.querySelectorAll(`section [data-lane="${lane}"] .board-card`);
      const shown = [...cards].filter((card) => this.laneShows(lane, card)).length;

      return `${shown} / ${total}`;
    },

    /** A lane's cards as tall as its row was dragged (else as tall as the page makes them). */
    sizeLane(cards) {
      const height = this.laneHeights[cards.dataset.lane];

      if (height) {
        cards.style.setProperty("height", `${height}px`);
        cards.style.setProperty("flex", "none"); // else the lane's column sizes it by its cards
        cards.style.setProperty("max-height", "none", "important");
      } else {
        ["height", "flex", "max-height"].forEach((name) => cards.style.removeProperty(name));
      }
    },

    /** The lanes on the same row as `lane` (the grid wraps them as the window allows). */
    rowOf(lane) {
      return [...lane.parentElement.querySelectorAll(":scope > section.lane")].filter(
        (other) => Math.abs(other.offsetTop - lane.offsetTop) < 4,
      );
    },

    /** Drag a lane's bottom edge: every lane of its row follows, so the row stays even. */
    resizeRow(event, lane) {
      const keys = this.rowOf(lane).map((other) => other.dataset.key);
      const startY = event.clientY;
      const startHeight = lane.querySelector("[data-lane]").getBoundingClientRect().height;

      const move = (moved) => {
        const height = Math.max(MIN_LANE_HEIGHT, Math.round(startHeight + moved.clientY - startY));

        this.laneHeights = { ...this.laneHeights, ...Object.fromEntries(keys.map((key) => [key, height])) };
      };

      const stop = () => {
        window.removeEventListener("pointermove", move);
        document.documentElement.classList.remove("no-select", "resizing-row");
      };

      document.documentElement.classList.add("no-select", "resizing-row");
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", stop, { once: true });
      window.addEventListener("pointercancel", stop, { once: true });
    },

    /** A double click on the edge: the row's lanes go back to their own height. */
    resetRow(lane) {
      const keys = this.rowOf(lane).map((other) => other.dataset.key);

      this.laneHeights = Object.fromEntries(
        Object.entries(this.laneHeights).filter(([key]) => !keys.includes(key)),
      );
    },

    /** A double click on a faculty's lane (not on a card or a button) opens its form. */
    editLane(event, url) {
      if (event.target.closest(".board-card, button, a, input, .lane-handle, .lane-resize")) return;

      window.getSelection()?.removeAllRanges(); // the double click selected a word
      this.openModal(url);
    },

    openModal(url) {
      window.htmx.ajax("GET", url, { target: "#modal-container", swap: "innerHTML" });
    },

    matches(name) {
      const query = this.search.trim().toLowerCase();
      return !query || name.toLowerCase().includes(query);
    },
  };
}

function csrfToken() {
  return document.querySelector("meta[name='csrf-token']")?.content || "";
}
