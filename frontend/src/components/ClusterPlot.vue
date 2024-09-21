<template>
  <div class="columns is-1">
    <div
      class="column is-one-quarter"
      :style="{ height: chartHeight, overflow: 'hidden', position: 'relative' }"
    >
      <div v-if="hoveredArticleError">
        <b-message
          title="Article Error"
          class="is-danger"
          :closable="false"
        >
          {{
            hoveredArticleError
          }}
        </b-message>
      </div>
      <div v-else-if="loadingHoveredArticle">
        <b-loading
          :active="true"
          :is-full-page="false"
          :can-cancel="false"
        />
      </div>
      <div v-else-if="hoveredArticle">
        <div class="has-text-centered mb-3">
          <div style="display: flex; align-items: center">
            <router-link
              :to="{
                name: 'article',
                params: { articleID: hoveredArticle.article_id },
              }"
              target="_blank"
              style="margin-right: 8px"
            >
              {{ hoveredArticle.title }}
              <b-icon icon="window-restore" />
            </router-link>
          </div>
        </div>
        <p>
          <strong>LitMapper Article ID:</strong>
          {{ hoveredArticle.article_id }}
        </p>
        <p>
          <strong>PubMed ID:</strong>
          {{ hoveredArticle.pmid }}
        </p>
        <p>
          <strong>Cluster:</strong>
          {{ hoveredArticle.cluster }}
        </p>
        <p>
          <strong>MeSH Terms:</strong>
          {{ formatMeshTerms(hoveredArticle.mesh_terms) }}
        </p>
        <p>
          <strong>Abstract:</strong>
          {{ hoveredArticle.abstract }}
        </p>
      </div>
      <div
        v-else
        class="has-text-centered"
      >
        <p class="subtitle is-5">
          Hover over a point to see the details on its corresponding article
          here.
        </p>
      </div>
    </div>
    <div class="column">
      <div :style="{ height: chartHeight }">
        <v-chart
          ref="echarts"
          :option="chartConfig"
          autoresize
          @finished.once="setBrush"
          @mouseover="echartsHandleArticleHover"
          @brushselected="echartsHandleSelection"
        />
      </div>
    </div>
  </div>
</template>
<script>
import { getArticle } from "@/api";
import debounce from "lodash/debounce";
import map from "lodash/map";
import join from "lodash/join";
import { ScatterChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { use } from "echarts/core";
import { BrushComponent, ToolboxComponent } from "echarts/components";

use([CanvasRenderer, ScatterChart, BrushComponent, ToolboxComponent]);

export default {
  name: "ClusterPlot",
  props: {
    scatterData: {
      type: Object,
      required: true,
    },
    groupIDs: {
      type: Object,
      required: true,
    },
  },
  data: () => ({
    loadingHoveredArticle: false,
    hoveredArticleError: null,
    hoveredArticle: null,
  }),
  computed: {
    chartConfig() {
      const formattedData = this.scatterData.x.map((_, i) => 
        ({ value: [this.scatterData.x[i], this.scatterData.y[i] ],
          itemStyle: {
            color: this.scatterData.marker.color[i],
            opacity: this.scatterData.marker.opacity[i],
          }
        })
      );
      const option = {
        grid: {
          show: true,
          top: 0,
          bottom: 0,
          left: 0,
          right: 0,
        },
        xAxis: {
          type: 'value',
          scale: true,
          axisTick: { show: false },
          splitLine: { show: false },
          show: false,
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisTick: { show: false },
          splitLine: { show: false },
          show: false,
        },
        series: [
          {
            type: 'scatter',
            data: formattedData,
          }
        ],
        brush: {
          xAxisIndex: 0,
          throttleType: 'debounce',
          throttleDelay: 300,
          toolbox: ['rect', 'polygon', 'clear']
        },
        toolbox: {
          show: true
        },
      };
      return option;
    },
    chartHeight() {
      return "600px";
    },
  },
  watch: {
    groupIDs: function () {
      //Picks up filtering done in concept graph
      this.brushSelectedGroupIDs = this.groupIDs;
      this.updateSelectedGroupIDs();
    },
  },
  methods: {
    updateSelectedGroupIDs() {
      this.selectedGroupIDs = this.brushSelectedGroupIDs;
      this.$emit("update:modelValue", this.brushSelectedGroupIDs);
      this.brushSelectedGroupIDs = null;
      // console.log(this.selectedGroupIDs);
    },
    setBrush() {
      // Set brush to polygon mode (lasso)
      this.$refs.echarts.dispatchAction({
        type: "takeGlobalCursor",
        key: "brush",
        brushOption: {
          brushType: "polygon",
          brushMode: "single",
        },
      });
    },
    echartsHandleArticleHover(event) {
      this.hoveredArticleError = null;
      this.echartsHoverGetInfo(event);
    },
    echartsHoverGetInfo: debounce(function (event) {
      // Load the article asynchronously and populate
      // the data when the response comes back
      const articleIndex = event.dataIndex;
      const eventData = this.scatterData;
      const articleID = eventData.extra.article_ids[articleIndex];

      // Only assign clusterID to articles without null cluster labels.
      let cluster = "None";
      if (eventData.extra.labels[articleIndex] !== null) {
        cluster = eventData.extra.labels[articleIndex];
      }

      getArticle(articleID)
        .then((article) => {
          this.loadingHoveredArticle = false;
          this.hoveredArticle = {
            ...article,
            cluster: cluster,
          };
        })
        .catch((err) => {
          this.loadingHoveredArticle = false;
          this.hoveredArticleError = err.message;
        });
    }, 200),
    echartsHandleSelection(params) {
      const brushedGroupIDs = {};
      const selectedPoints = params.batch[0].selected[0].dataIndex;
      for (const point of selectedPoints) {
        const pointGroupID = this.scatterData.extra.labels[point];
        brushedGroupIDs[pointGroupID] = true;
      }
      this.brushSelectedGroupIDs = brushedGroupIDs;
      const formattedData = this.scatterData.x.map((_, i) => 
        ({ value: [this.scatterData.x[i], this.scatterData.y[i] ],
          itemStyle: {
            color: this.scatterData.marker.color[i],
            opacity: selectedPoints.length === 0 || this.scatterData.extra.labels[i] in brushedGroupIDs ? 0.8 : 0.2,
          }
        })
      );
      this.$refs.echarts.setOption({
        series: [
          {
            type: 'scatter',
            data: formattedData,
          }
        ],
      });
      this.updateSelectedGroupIDs();
      this.$refs.echarts.dispatchAction({
        type: "brush",
        areas: [],
      });
    },
    formatMeshTerms(meshTerms) {
      return join(
        map(meshTerms, (t) => t.name),
        " | "
      );
    },
  },
  emits: ["update:modelValue"],
};
</script>
