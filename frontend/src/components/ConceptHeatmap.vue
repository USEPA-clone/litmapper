<template>
  <div
    v-if="emptySelection"
    class="has-text-centered"
  >
    <p class="subtitle">
      No clusters selected by the current filter combination.
    </p>
  </div>
  <div
    v-else-if="selectionTooLarge"
    class="has-text-centered"
  >
    <p class="subtitle">
      You must select no more than {{ MAX_GROUP_IDS }} clusters for the concept
      heatmap to display.
    </p>
  </div>
  <div v-else>
    <div :style="{ height: chartHeight }">
      <v-chart
        ref="echarts"
        :option="chartConfig"
        :autoresize="false"
      />
    </div>
  </div>
</template>
<script>
import size from "lodash/size";
import keys from "lodash/keys";
import forEach from "lodash/forEach";
import isNil from "lodash/isNil";
import union from "lodash/union";
import update from "lodash/update";

import { HeatmapChart } from "echarts/charts";
import { VisualMapComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { use } from "echarts/core";

use([CanvasRenderer, HeatmapChart, VisualMapComponent, TooltipComponent]);

export default {
  name: "ConceptHeatmap",
  props: {
    selectedGroupIDs: {
      type: Object,
      required: true,
    },
    articleGroups: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      MAX_GROUP_IDS: 10,
      mapColors: [
        [0, "hsl(0, 0, 100%)"],
        [0.5, "hsl(256, 60%, 95%)"],
        [1, "hsl(256, 60%, 48%)"],
      ],
      heatmapInfo: {},
    };
  },
  computed: {
    chartConfig() {
      // Transform this.heatmapInfo.z to an array of coordinates and values
      const data = this.heatmapInfo.z.reduce((acc, row, i) => {
        row.forEach((value, j) => {
          acc.push([j, i, value]);
        });
        return acc;
      }, []);

      return {
        tooltip: {
          position: 'top',
          formatter: (params) => {
            return `<b>${this.heatmapInfo.x[params.data[0]]}</b><br>${this.heatmapInfo.y[params.data[1]]}`;
          },
        },
        legend: {
          show: false
        },
        grid: {
          left: '18%',
        },
        xAxis: {
          type: 'category',
          data: this.heatmapInfo.x,
          splitArea: {
            show: true
          }
        },
        yAxis: {
          type: 'category',
          data: this.heatmapInfo.y,
          splitArea: {
            show: true
          }
        },
        visualMap: {
          min: 0,
          max: 1,
          show: false,
          inRange: {
            color: this.mapColors.map((color) => color[1])
          }
        },
        series: [
          {
            type: 'heatmap',
            data: data,
            label: {
              show: false
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.5)',
                color: "hsl(256, 45%, 75%)"
              }
            }
          }
        ]
      };
    },
    chartHeight() {
      // Hack to resize the chart after the height is determined
      // eslint-disable-next-line vue/no-async-in-computed-properties
      window.setTimeout(() => {
        this.$refs.echarts.resize();
      }, 50);
      return this.heatmapInfo.y.length * 40 > 400
        ? `${this.heatmapInfo.y.length * 40}px`
        : "400px";
    },
    selectionTooLarge() {
      return size(this.selectedGroupIDs) > this.MAX_GROUP_IDS;
    },
    emptySelection() {
      return size(this.selectedGroupIDs) === 0;
    },
    termCounts() {
      let termCounts = {};
      forEach(keys(this.selectedGroupIDs), (groupID) => {
        const groupNdx = this.groupIDNdx[groupID];
        forEach(this.groupSummaryTerms[groupNdx], (term) => {
          update(termCounts, term, (val) => (isNil(val) ? 1 : val + 1));
        });
      });
      return termCounts;
    },
  },
  watch: {
    selectedGroupIDs: function () {
      this.heatmapInfo = this.getHeatmapInfo();
    },
  },
  beforeMount() {
    this.heatmapInfo = this.getHeatmapInfo();
  },
  methods: {
    getHeatmapInfo() {
      let selectedGroups = Object.keys(this.selectedGroupIDs);
      let heatmapTerms = this.getHeatmapTerms(selectedGroups);
      let heatmapFrequencies = this.getHeatmapFrequencies(
        heatmapTerms,
        selectedGroups
      );
      let heatmapClusterLabels = this.getHeatmapClusters(selectedGroups);

      return {
        x: heatmapClusterLabels,
        y: heatmapTerms,
        z: heatmapFrequencies,
      };
    },

    getHeatmapTerms(selectedGroups) {
      let heatmapTerms = [];
      this.articleGroups.forEach((group) => {
        if (selectedGroups.includes(String(group.id))) {
          heatmapTerms = union(heatmapTerms, group.top_terms);
        }
      });
      return heatmapTerms;
    },

    getHeatmapClusters(selectedGroups) {
      let xLabels = selectedGroups.map((id) => {
        return "Cluster " + String(id);
      });
      return xLabels;
    },

    getHeatmapFrequencies(heatmapTerms, selectedGroups) {
      let heatmapFrequencies = [];
      heatmapTerms.forEach((term) => {
        let termFreqArray = [];
        this.articleGroups.forEach((group) => {
          if (selectedGroups.includes(String(group.id))) {
            if (group.top_terms.includes(term)) {
              termFreqArray.push(1);
            } else {
              termFreqArray.push(null);
            }
          }
        });
        heatmapFrequencies.push(termFreqArray);
      });
      return heatmapFrequencies;
    },
  },
};
</script>

<style scoped>
</style>
