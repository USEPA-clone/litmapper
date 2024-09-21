<template>
  <div>
    <div class="card">
      <header class="card-header">
        <p class="card-header-title">
          Explore Articles
        </p>
      </header>
      <div class="card-content">
        <div class="section">
          <div class="has-text-centered">
            <p class="subtitle is-3 mb-3">
              Cluster Plot
            </p>
          </div>
          <p class="mb-3">
            This chart plots similar articles near each other as points and
            colors them according to cluster. You can mouse over a point to see
            more details about an article. You can also use your mouse to pan
            (click and drag) and zoom (mouse wheel) around the plot.
          </p>
          <p class="mb-3">
            To select clusters for further exploration and export, use the brush
            tools. Select a brush (rectangular or polygon lasso) with the tools
            at the top right of the chart. Click and drag on the chart to apply
            the brush. Once you release the mouse, any clusters partially
            covered by the brush will be added to the current selection.
            Creating a new brush resets the selection. To reset the selection to
            all clusters, you can either select them all or select none of them.
          </p>
          <p class="mb-5">
            This chart is linked to the graph below -- applying a filter on one
            filters the other and overwrites the filter on the other, if any.
          </p>
          <ClusterPlot
            v-model="selectedGroupIDs"
            :group-i-ds="clusterPlotGroupIDs"
            :scatter-data="clusteringData.plotly_data"
          />
        </div>
        <div class="section">
          <div class="has-text-centered">
            <p class="subtitle is-3 mb-3">
              Concept Graph
            </p>
          </div>
          <p class="mb-3">
            This chart shows the top concepts present in the current selected
            clusters. Larger nodes mean the term is contained in more clusters.
            An edge means the two terms co-occur in at least one cluster. Hover
            over a node to see the name of the concept associated with that node
            and the names of any concepts which co-occur in clusters with that
            concept. You can use the input below to select one or more concepts
            in the graph, which will filter the clusters to only those
            containing one or more of the selected concepts.
          </p>
          <p class="mb-3">
            Note the graph displays only the top terms by frequency in order to
            avoid hanging up the browser, but you can select from any of the
            present terms using the below input.
          </p>
          <p class="mb-5">
            This graph is linked to the chart above -- applying a filter on one
            filters the other and overwrites the filter on the other, if any.
          </p>
          <ConceptGraph
            v-model="selectedGroupIDs"
            :group-i-ds="conceptGraphGroupIDs"
            :group-summary-terms="conceptGraphTopTerms"
          />
        </div>
        <div class="section">
          <div class="has-text-centered">
            <p class="subtitle is-3 mb-3">
              Cluster Heatmap
            </p>
          </div>
          <p class="mb-5">
            This heatmap shows the similarities and differences in terms of
            concepts between clusters. You must select a subset of clusters
            using the above visualizations for the heatmap to display.
          </p>
          <ConceptHeatmap
            :article-groups="articleGroupData.result"
            :selected-group-i-ds="selectedGroupIDs"
          />
        </div>
        <div class="section">
          <div class="has-text-centered">
            <p class="subtitle is-3 mb-3">
              Create Article Set
            </p>
          </div>
          <p class="mb-5">
            After filtering the article clusters using either of the two charts
            above, you can save a subset of the filtered clusters as a
            persistent article set which can be exported and browsed later.
            Enter a name for the article set, check the clusters you want to
            include, and click the button below to save the article set.
          </p>
          <ArticleSetCreator
            :article-groups="selectedGroupArticleIDs"
            :article-group-params="articleGroupParams"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ClusterPlot from "@/components/ClusterPlot.vue";
import ConceptGraph from "@/components/ConceptGraph.vue";
import ConceptHeatmap from "@/components/ConceptHeatmap.vue";
import ArticleSetCreator from "@/components/ArticleSetCreator.vue";

export default {
  name: "ArticleGroupExplorer",
  components: {
    ClusterPlot,
    ConceptGraph,
    ConceptHeatmap,
    ArticleSetCreator,
  },
  props: {
    clusteringData: {
      type: Object,
      required: true,
    },
    articleGroupData: {
      type: Object,
      required: true,
    },
    articleGroupParams: {
      type: Object,
      required: true,
    },
  },
  data() {
    let selectedGroupIDs = {};
    for (const group of this.articleGroupData.result) {
      selectedGroupIDs[group.id] = true;
    }

    return {
      selectedGroupIDs,
    };
  },
  computed: {
    //Holdover properties make concept graph work with new data structure.
    // Concept graph to be removed or ported to Plotly in next iteration.
    conceptGraphGroupIDs() {
      let groupIDs = this.articleGroupData.result.map((group) => {
        return group.id;
      });
      return groupIDs;
    },
    clusterPlotGroupIDs() {
      //Allows concept graph component to filter cluster plot
      return this.selectedGroupIDs;
    },
    conceptGraphTopTerms() {
      let top_terms = this.articleGroupData.result.map((group) => {
        return group.top_terms;
      });
      return top_terms;
    },
    selectedGroupArticleIDs() {
      //Produces object with keys = Selected Article Group IDs and
      // values = articles in group. Used in ArticleSetCreator.
      let selectedGroupArticleIDs = [];
      this.articleGroupData.result.forEach((groupInfo) => {
        if (Object.keys(this.selectedGroupIDs).includes(String(groupInfo.id))) {
          selectedGroupArticleIDs.push({
            id: groupInfo.id,
            articleIDs: groupInfo.article_ids,
          });
        }
      });
      return selectedGroupArticleIDs;
    },
  },
};
</script>
