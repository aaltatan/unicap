import { ArcElement, Chart, DoughnutController, Tooltip } from "chart.js";

Chart.register(DoughnutController, ArcElement, Tooltip);

/**
 * How a faculty is filled: a doughnut of its counted PhDs (no masters). The outer ring is
 * every kind (specialized fulltime, ...) of each employment, the inner ring staff / borrowed;
 * a kind takes its employment's color, darker for the more expensive kinds.
 * The numbers come from the domain (`FacultyReport.composition`), read from a json_script.
 */
const SHADES = {
  staff: ["#3730a3", "#4f46e5", "#6366f1", "#818cf8", "#c7d2fe"],
  borrowed: ["#92400e", "#d97706", "#f59e0b", "#fbbf24", "#fde68a"],
};

const GROUP = { staff: "#4338ca", borrowed: "#b45309" };

const KINDS = [
  "specialized_fulltime",
  "supported_fulltime",
  "specialized_parttime",
  "supported_parttime",
  "master",
];

export function compositionChart(dataId) {
  let chart = null; // not reactive: Chart.js does not work through Alpine's proxies

  return {
    data: { slices: [], groups: [], total: 0 },

    init() {
      this.data = JSON.parse(document.getElementById(dataId).textContent);

      if (!this.data.total) return;

      const border = getComputedStyle(this.$el).getPropertyValue("--chart-gap").trim() || "#fff";

      // the inner ring: one arc per group, as wide as its slices together
      // (slices come staff first: each group's total sits on its first slice, the rest 0)
      const inner = this.data.slices.map((slice) =>
        slice.kind === this.firstOf(slice.employment).kind ? this.groupOf(slice.employment).count : 0,
      );

      chart = new Chart(this.$refs.canvas, {
        type: "doughnut",
        data: {
          labels: this.data.slices.map((slice) => slice.label),
          datasets: [
            {
              data: this.data.slices.map((slice) => slice.count),
              backgroundColor: this.data.slices.map((slice) => this.color(slice)),
              borderColor: border,
              borderWidth: 2,
            },
            {
              data: inner,
              backgroundColor: this.data.slices.map((slice) => GROUP[slice.employment]),
              borderColor: border,
              borderWidth: 2,
              groupLabels: this.data.slices.map((slice) => this.groupOf(slice.employment).label),
            },
          ],
        },
        options: {
          cutout: "45%",
          maintainAspectRatio: false,
          animation: { duration: 300 },
          plugins: {
            legend: { display: false }, // the legend is HTML: translated, right-to-left aware
            tooltip: {
              rtl: document.documentElement.dir === "rtl",
              callbacks: {
                label: (item) =>
                  item.datasetIndex === 1
                    ? ` ${item.dataset.groupLabels[item.dataIndex]}: ${item.raw}`
                    : ` ${item.label}: ${item.raw}`,
              },
            },
          },
        },
      });
    },

    destroy() {
      chart?.destroy();
    },

    firstOf(employment) {
      return this.data.slices.find((slice) => slice.employment === employment);
    },

    groupOf(employment) {
      return this.data.groups.find((group) => group.employment === employment);
    },

    color(slice) {
      return SHADES[slice.employment][KINDS.indexOf(slice.kind)];
    },
  };
}
