import collapse from "@alpinejs/collapse";
import focus from "@alpinejs/focus";
import mask from "@alpinejs/mask";
import persist from "@alpinejs/persist";
import sort from "@alpinejs/sort";
import Autosize from "@marcreichel/alpine-autosize";
import Alpine from "alpinejs";
import htmx from "htmx.org";

import "../css/main.css";

import { board } from "./src/board";
import { compositionChart } from "./src/charts";
import { preventSelectionWhileDragging } from "./src/drag";
import { formset } from "./src/formset";
import { dropdown, layout, persistedOrder, themeStore, toast } from "./src/layout";
import { matches, searchSelect } from "./src/search-select";
import { shortcutsOnAnyLayout } from "./src/shortcuts";
import { rememberPageState } from "./src/state";
import { storage } from "./src/storage";
import { exportUrl, rowMenu, tableColumns, tableSelection } from "./src/table";
import { tooltips } from "./src/tooltip";

window.htmx = htmx;
window.Alpine = Alpine;

htmx.config.globalViewTransitions = false;
htmx.config.defaultSwapStyle = "innerHTML";
htmx.config.historyCacheSize = 0;
htmx.config.refreshOnHistoryMiss = true;

Alpine.plugin(collapse);
Alpine.plugin(focus);
Alpine.plugin(mask);
Alpine.plugin(persist);
Alpine.plugin(sort);
Alpine.plugin(Autosize);

// templates persist through the same namespaced storage: $persist(...).as(...).using($storage)
Alpine.magic("storage", () => storage);
Alpine.magic("exportUrl", () => exportUrl);
Alpine.magic("matches", () => matches);

document.addEventListener("alpine:init", () => {
  Alpine.store("theme", themeStore(Alpine));

  Alpine.data("layout", layout);
  Alpine.data("dropdown", dropdown);
  Alpine.data("toast", toast);
  Alpine.data("persistedOrder", persistedOrder);
  Alpine.data("tableColumns", tableColumns);
  Alpine.data("tableSelection", tableSelection);
  Alpine.data("rowMenu", rowMenu);
  Alpine.data("board", board);
  Alpine.data("compositionChart", compositionChart);
  Alpine.data("formset", formset);
  Alpine.data("searchSelect", searchSelect);
});

preventSelectionWhileDragging();
shortcutsOnAnyLayout();
tooltips();
rememberPageState();

Alpine.start();
