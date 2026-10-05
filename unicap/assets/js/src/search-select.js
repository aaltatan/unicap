/**
 * A <select> you search by typing: `<div x-data="searchSelect">` around a native select.
 *
 * The native select stays in the form (hidden) and is what is submitted, so the server
 * side does not change; the text input above it filters its options as you type
 * (↑ ↓ to move, Enter to pick, Esc to close). Every typed word must appear, in any order,
 * ignoring case, Arabic diacritics, spelling variants and a leading article.
 */

// as app/utils/text.py does on the server: one spelling per letter, no diacritics
const LETTERS = { "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي" };
const MARKS = /[ً-ْٰـ]/g;
const ARTICLES = ["وال", "بال", "فال", "كال", "لل", "ال"];

/** Text as it is compared: "إدارةُ الأعمال" and "اداره الاعمال" are the same. */
export function normalize(text) {
  return String(text ?? "")
    .toLowerCase()
    .replace(/[أإآٱةىؤئ]/g, (letter) => LETTERS[letter])
    .replace(MARKS, "")
    .trim();
}

/** The words of a search, normalized, a leading Arabic article dropped ("العمارة" -> "عماره"). */
export function searchTerms(query) {
  return normalize(query)
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => {
      const article = ARTICLES.find((a) => word.startsWith(a) && word.length - a.length >= 3);
      return article ? word.slice(article.length) : word;
    });
}

/** Every word of `query`, in any order, inside `text`: "هند عمار" finds "هندسة العمارة". */
export function matches(text, query) {
  const haystack = normalize(text);
  return searchTerms(query).every((term) => haystack.includes(term));
}

export function searchSelect() {
  return {
    query: "",
    isOpen: false,
    typed: false,
    active: 0,
    options: [],
    // declared here: Alpine sets an undeclared property on the outermost scope (the page's),
    // where every search select would share one `select`, the last one drawn
    select: null,

    init() {
      this.select = this.$el.querySelector("select");
      const input = this.$refs.input;

      // the visible input takes the select's place: its label, `required` and state
      input.required = this.select.required;
      input.disabled = this.select.disabled;
      this.select.required = false;
      this.select.tabIndex = -1;

      if (this.select.id) {
        input.id = this.select.id;
        this.select.id = `${this.select.id}-select`;
      }

      if (this.select.getAttribute("aria-invalid")) {
        input.setAttribute("aria-invalid", this.select.getAttribute("aria-invalid"));
      }

      this.query = this.selectedLabel();
      this.select.addEventListener("change", () => {
        this.query = this.selectedLabel();
      });
    },

    get filtered() {
      if (!this.typed || !searchTerms(this.query).length) return this.options;

      return this.options.filter((option) => matches(option.label, this.query));
    },

    readOptions() {
      return [...this.select.options].map((option) => ({
        value: option.value,
        label: option.value === "" ? "—" : option.textContent.trim(),
      }));
    },

    selectedLabel() {
      const option = this.select.selectedOptions[0];
      return option && option.value !== "" ? option.textContent.trim() : "";
    },

    open() {
      if (this.isOpen || this.$refs.input.disabled) return;

      this.options = this.readOptions();
      this.active = Math.max(
        0,
        this.options.findIndex((option) => option.value === this.select.value),
      );
      this.isOpen = true;
      this.$nextTick(() => this.reveal());
    },

    type() {
      this.open();
      this.typed = true;
      this.active = 0;
    },

    move(step) {
      if (!this.isOpen) return this.open();

      const count = this.filtered.length;
      if (!count) return undefined;

      this.active = (this.active + step + count) % count;
      this.$nextTick(() => this.reveal());
      return undefined;
    },

    pick(option) {
      if (!option) return;

      this.select.value = option.value;
      this.select.dispatchEvent(new Event("change", { bubbles: true }));
      this.close();
    },

    close() {
      this.isOpen = false;
      this.typed = false;
      this.query = this.selectedLabel();
    },

    reveal() {
      this.$refs.list?.querySelector("[data-active]")?.scrollIntoView({ block: "nearest" });
    },
  };
}
