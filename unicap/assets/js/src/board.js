/**
 * The drag-and-drop board (Alpine sort, i.e. SortableJS, between lanes).
 *
 * When a card is picked up, the server evaluates every drop it could make and returns,
 * per lane, whether the contract would be counted there and what the capacity would
 * become. While dragging, the hovered lane is outlined with that color and the hint
 * shows it; dropping posts the move and the server re-renders the board.
 * Nothing is decided here: the colors and texts come from the domain's evaluation.
 */
export function board({ previewUrl, moveUrl, toggleUrl }) {
  return {
    previews: {},
    hovered: null,
    sourceLane: null,
    hint: "",
    dragging: false,
    search: "",
    clickTimer: null,

    get sortConfig() {
      return {
        animation: 150,
        ghostClass: "opacity-40",
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

    toggle(employee) {
      window.htmx.ajax("POST", toggleUrl, {
        target: "#board",
        swap: "outerHTML",
        values: { employee },
        headers: { "X-CSRFToken": csrfToken() },
      });
    },

    // a click opens the details, a double-click switches the contract: wait to tell them apart
    clickCard(url) {
      window.clearTimeout(this.clickTimer);
      this.clickTimer = window.setTimeout(() => {
        window.htmx.ajax("GET", url, { target: "#modal-container", swap: "innerHTML" });
      }, 250);
    },

    doubleClickCard(employee) {
      window.clearTimeout(this.clickTimer);
      this.toggle(employee);
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
