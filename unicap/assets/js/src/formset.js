/**
 * An inline formset edited in place: add rows from a <template>, mark rows deleted,
 * and drag rows to reorder them (each row's `position` input follows its place).
 *
 * A removed row, saved or new, stays in the form, hidden and marked DELETE: the formset
 * skips its validation (an empty new row needs nothing filled), and the form count stays
 * right. Its fields stop being `required`, so the browser does not block the submit.
 */
export function formset(prefix) {
  return {
    prefix,

    init() {
      // rows removed before a failed submit come back hidden: they need nothing filled
      this.$refs.rows.querySelectorAll("[data-row].hidden [required]").forEach((field) => {
        field.required = false;
      });

      this.$nextTick(() => this.renumber());
    },

    totalInput() {
      return this.$root.querySelector(`input[name='${this.prefix}-TOTAL_FORMS']`);
    },

    add() {
      const total = this.totalInput();
      const index = Number(total.value);
      const html = this.$refs.template.innerHTML.replaceAll("__prefix__", index);

      this.$refs.rows.insertAdjacentHTML("beforeend", html);
      total.value = index + 1;
      this.renumber();

      // the new row's first field (its search box): after Alpine has set the row up, so
      // focusing it opens the list of choices
      const row = [...this.$refs.rows.querySelectorAll("[data-row]")].at(-1);
      setTimeout(() => {
        row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        const field = row?.querySelector("[role=combobox]") ?? row?.querySelector(
          "select:not([tabindex='-1']), input:not([type=hidden])",
        );
        field?.focus();
      });
    },

    remove(row) {
      const deleteBox = row.querySelector("input[name$='-DELETE']");

      if (deleteBox) deleteBox.checked = true;

      row.querySelectorAll("[required]").forEach((field) => {
        field.required = false;
      });
      row.classList.add("hidden");

      this.renumber();
    },

    renumber() {
      [...this.$refs.rows.querySelectorAll("[data-row]:not(.hidden)")].forEach((row, index) => {
        const position = row.querySelector("input[name$='-position']");
        if (position) position.value = index;
      });
    },
  };
}
