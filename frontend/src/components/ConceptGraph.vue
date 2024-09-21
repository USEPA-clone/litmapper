<template>
  <div>
    <div>
      <b-field
        grouped
        position="is-centered"
      >
        <b-tooltip animated>
          <b-taginput
            v-model="selectedTerms"
            autocomplete
            :data="termNames"
            :open-on-focus="true"
            icon="magnify"
            placeholder="Choose one or more terms"
            expanded
            clearable
            width="100%"
            @typing="setAutocompleteText"
            @input="clearAutocompleteText"
          />
          <template #content>
            Choose one or more top concept terms associate with the nodes.
          </template>
        </b-tooltip>
        <b-tooltip animated>
          <b-select v-model="filterMode">
            <option value="AND">
              AND (Cluster Contains All Terms)
            </option>
            <option value="OR">
              OR (Cluster Contains At Least One Term)
            </option>
          </b-select>
          <template #content>
            Select the type of clustering.
          </template>
        </b-tooltip>
        <p class="control">
          <b-button
            type="is-primary"
            @click="applyFilter"
          >
            Apply Filter
          </b-button>
        </p>
      </b-field>
    </div>
    <div
      v-if="emptySelection"
      class="has-text-centered mt-5 mb-5"
    >
      <p class="subtitle">
        No clusters selected by the current filter combination.
      </p>
    </div>
    <div
      v-else
      :style="{ height: chartHeight }"
    >
      <v-chart
        ref="chart"
        :option="chartConfig"
        :autoresize="true"
      />
    </div>
  </div>
</template>

<script>
import forEach from "lodash/forEach";
import sortBy from "lodash/sortBy";
import get from "lodash/get";
import set from "lodash/set";
import map from "lodash/map";
import keys from "lodash/keys";
import isNil from "lodash/isNil";
import update from "lodash/update";
import max from "lodash/max";
import slice from "lodash/slice";
import has from "lodash/has";
import size from "lodash/size";
import { filterTexts } from "@/util";
import { GraphChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { use } from "echarts/core";

use([CanvasRenderer, GraphChart]);

export default {
  name: "ConceptGraph",
  props: {
    groupSummaryTerms: {
      type: Array,
      required: true,
    },
    groupIDs: {
      type: Array,
      required: true,
    },
    modelValue: {
      type: Object,
      required: true,
    },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      NUM_TOP_CONCEPTS: 30,
      filteredTermCounts: {},
      allTerms: {},
      selectedTerms: [],
      termGroups: {},
      autocompleteText: "",
      filterMode: "AND",
      chart: null,
      isChartInitialized: false,
    };
  },
  computed: {
    emptySelection() {
      return size(this.modelValue) === 0;
    },
    termNames() {
      const names = sortBy(keys(this.allTerms));
      return filterTexts(this.autocompleteText, names);
    },
    chartHeight() {
      return "600px";
    },
    chartConfig() {
      const graphData = this.getGraphData();
      return {
        series: [
          {
            type: "graph",
            nodes: graphData.termNodes,
            links: graphData.termLinks,
            roam: true,
            layout: "force",
            focus: "adjacency",
            zoom: 2.5,
            color: "#7957d5",
            label: {
              show: false,
              position: "center",
              formatter: "{b}"
            },
            emphasis: {
              focus: "adjacency",
              label: {
                show: true
              }
            },
            force: {
              repulsion: 20,
              friction: 0.1
            },
            edgeSymbolSize: [4, 10],
          },
        ], 
        tooltip: {
          show: false
        }
      };
    },
  },
  watch: {
    chartConfig: {
      handler() {
        this.updateChart();
      },
      deep: true
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.initializeChart();
    });
  },
  updated() {
    this.$nextTick(() => {
      this.initializeChart();
    });
  },
  methods: {
    applyFilter() {
      const filterSelectedGroupIDs = {};
      forEach(this.groupIDs, (groupID) => {
        if (this.filterMode === "AND") {
          // Each group must contain all filter terms
          let allTermsMatched = true;
          for (const term of this.selectedTerms) {
            if (!get(this.termGroups, [term, groupID])) {
              allTermsMatched = false;
              break;
            }
          }
          if (allTermsMatched) {
            filterSelectedGroupIDs[groupID] = true;
          }
        } else if (this.filterMode === "OR") {
          // Each group must contain at least one filter term
          for (const term of this.selectedTerms) {
            if (get(this.termGroups, [term, groupID])) {
              filterSelectedGroupIDs[groupID] = true;
              break;
            }
          }
        }
      });

      this.$emit("update:modelValue", filterSelectedGroupIDs);
    },
    getGraphData() {
      // TODO echarts allows for categories in the graph -- would be great
      // to apply semantic types as categories once we start getting this info from UMLS

      // Need to reshape the input data into a node list and a list of links for echarts
      let termLinkCounts = {};

      // Track max count for a term to scale node size
      let maxCount = 1;

      // Record which terms match the current filter so we can apply later to filter the
      // graph.
      this.filteredTermCounts = {};

      // Record all terms so we can populate the filter dropdown.
      this.allTerms = {};

      // Record which groups are associated with each term for term filters.
      this.termGroups = {};

      forEach(this.groupIDs, (groupID, groupNdx) => {
        // Echarts seems to only support directed graphs, so we need to avoid redundancy
        // in the edges while still accumulating the correct counts for this conceptually
        // undirected graph. Do this by sorting terms
        // first before counting edges, so our edges always go in the same direction.
        const sortedTerms = sortBy(this.groupSummaryTerms[groupNdx]);
        for (let i = 0; i < sortedTerms.length; i++) {
          const t1 = sortedTerms[i];
          this.allTerms[t1] = true;

          set(this.termGroups, [t1, groupID], true);

          // Only keep the term count and edges if the group matches the current filter
          if (has(this.modelValue, groupID)) {
            this.filteredTermCounts[t1] =
              get(this.filteredTermCounts, t1, 0) + 1;
            maxCount = max([maxCount, this.filteredTermCounts[t1]]);

            for (let j = i + 1; j < sortedTerms.length; j++) {
              const t2 = sortedTerms[j];
              update(termLinkCounts, [t1, t2], (val) =>
                isNil(val) ? 1 : val + 1
              );
            }
          }
        }
      });

      const termLinks = [];
      forEach(termLinkCounts, (t1Terms, t1) => {
        forEach(t1Terms, (count, t2) => {
          termLinks.push({
            source: t1,
            target: t2,
            value: count,
          });
        });
      });

      // ...and we only want nodes if they're in at least one of the filtered edges
      // Keep only the top nodes to avoid the graph getting too large
      const termNodes = slice(
        map(this.filteredTermCounts, (count, term) => ({
          name: term,
          value: count,
          symbolSize: (count / maxCount) * 20,
          label: {
            show: false
          }
        })),
        0,
        this.NUM_TOP_CONCEPTS
      );

      return {
        termNodes,
        termLinks,
      };
    },
    setAutocompleteText(text) {
      this.autocompleteText = text;
    },
    clearAutocompleteText() {
      this.autocompleteText = "";
    },
    // The rest of the methods are to allow for labels appearing on connected nodes
    // since echarts doesn't support this out of the box.
    getConnectedNodes(nodeName) {
      return this.chartConfig.series[0].links
        .filter(link => link.source === nodeName || link.target === nodeName)
        .map(link => link.source === nodeName ? link.target : link.source);
    },
    initializeChart() {
      if (this.$refs.chart) {
        this.chart = this.$refs.chart.chart;
        this.setupChartEventListeners();
        this.updateChart();
        this.isChartInitialized = true;
      }
    },
    updateChart() {
      if (this.chart) {
        this.chart.setOption(this.chartConfig);
        this.setupChartEventListeners();
      }
    },
    setupChartEventListeners() {
      if (!this.chart) return;

      // Remove existing event listeners to prevent duplication
      this.chart.off('mouseover');
      this.chart.off('mouseout');

      this.chart.on('mouseover', { dataType: 'node' }, (params) => {
        const node = params.data;
        const connectedNodes = this.getConnectedNodes(node.name);
        
        this.chart.setOption({
          series: [{
            data: this.chartConfig.series[0].nodes.map(n => {
              if (n.name === node.name || connectedNodes.includes(n.name)) {
                return { ...n, label: { show: true } };
              }
              return { ...n, label: { show: false } };
            })
          }]
        });
      });

      this.chart.on('mouseout', { dataType: 'node' }, () => {
        this.chart.setOption({
          series: [{
            data: this.chartConfig.series[0].nodes.map(n => ({ ...n, label: { show: false } }))
          }]
        });
      });
    },
  },
};
</script>

<style scoped>
.echarts {
  width: 100%;
  height: 100%;
}

#app > section > div > div > div > section.section.pt-0.pb-0 > div > div > div > div:nth-child(2) > div:nth-child(5) > div:nth-child(1) > div > div > div > div:nth-child(1) {
  width: 100%;
}
</style>
