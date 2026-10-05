import containerQueries from "@tailwindcss/container-queries";
import scrollbar from "tailwind-scrollbar";
import plugin from "tailwindcss/plugin";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["unicap/templates/**/*.html", "unicap/app/**/*.py", "unicap/assets/**/*.js"],
  // dark styles on screen only: a page printed in dark mode prints light, on white paper
  darkMode: ["variant", "@media not print { .dark & }"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans Arabic"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [
    containerQueries,
    scrollbar({ nocompatible: true }),
    plugin(({ addVariant }) => {
      addVariant("hx-request", ["&.htmx-request", ".htmx-request &"]);
      addVariant("hx-swap", "&.htmx-swapping");
      addVariant("active", "&.active");
      addVariant("sorting", "&.sortable-chosen");
      addVariant("ghost", "&.sortable-ghost");
    }),
  ],
};
