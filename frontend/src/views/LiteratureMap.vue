<template>
  <div class="container">
    <div :class="{ 'disable-interaction': showModal }">
      <h1 class="title">
        Literature Map
      </h1>
      <b-tabs
        id="whole_tab"
        v-model="activeParameterTab"
      >
        <b-tab-item
          id="select_tab"
          label="Select Parameters"
        >
          <TagFilters
            v-model="tagFilters"
          />
          <AdvancedOptions
            id="advanced_options"
            v-model="advancedOptions"
            :article-group-params="rawArticleGroupParams"
            :clustering-params="rawClusteringParams"
          />
        </b-tab-item>
        <b-tab-item
          id="paste_tab"
          label="Paste Parameters"
        >
          <p class="mb-3">
            Paste raw JSON for an ArticleGroupParams object here to use it for the
            analysis instead of the user-selected parameters.
          </p>
          <b-field label="Parameter JSON">
            <b-input
              v-model="pastedParameterJSON"
              type="textarea"
            />
          </b-field>
        </b-tab-item>
        <b-tab-item
          id="pubmed_tab"
          label="Add PubMed Batch"
        >
          <PubmedBatchAnalysis
            v-model="tagFilters"
            :article-batches="articleBatches"
            :article-batch-search="articleBatchSearch"
            :selected-batch-articles="selectedBatchArticles"
            :update-article-batches="updateArticleBatches"
            :update-batch-queries="updateBatchQueries"
          />
        </b-tab-item>
      </b-tabs>

      <section
        v-if="paramsErrorMessage"
        class="section"
      >
        <b-message
          title="Parameter Error"
          class="is-danger"
          :closable="false"
        >
          {{ paramsErrorMessage }}
        </b-message>
      </section>

      <section
        v-if="showArticleCount"
        class="section pt-0"
      >
        <FilterSetDisplayBatch
          v-if="selectedBatchArticles.length > 0"
          class="mb-5"
          :batch-queries="selectedBatchQueries"
          :count="selectedBatchArticles.length"
        />
        <FilterSetDisplay :count="articleCount" />
      </section>

      <div class="has-text-centered mb-5">
        <b-button
          type="is-primary"
          size="is-large"
          @click="submit"
        >
          Run Analysis
        </b-button>
      </div>

      <section
        ref="articleGroupExplorerSection"
        class="section pt-0 pb-0"
      >
        <ArticleGroupExplorer
          v-if="clusteringResult && articleGroupResult"
          :clustering-data="clusteringResult"
          :article-group-data="articleGroupResult"
          :article-group-params="getArticleGroupParams()"
        />
      </section>
    </div>
    

    <b-modal
      v-model="showModal"
      :can-cancel="false"
      class="custom-modal"
    >
      <div
        id="status-modal"
        class="card"
      >
        <section>
          <b-progress
            v-if="!filterSetError && !clusteringError && !articleGroupError"
            animated
            type="is-primary"
            class="pt-3 px-3"
          />
        </section>

        <div class="card-content">
          <b-message
            v-if="filterSetStatus"
            title="Filter Set Status"
            class="mt-3 my-table"
            :closable="false"
          >
            {{ filterSetStatus }}
          </b-message>
          <APIErrorMessage
            title="Filter Set Error"
            :err="filterSetError"
          />

          <b-message
            v-if="clusteringStatus"
            title="Clustering Status"
            class="mt-3 my-table"
            :closable="false"
          >
            {{ clusteringStatus }}
          </b-message>
          <APIErrorMessage
            title="Clustering Error"
            :err="clusteringError"
          />
          <b-message
            v-if="articleGroupStatus"
            title="Article Group Status"
            class="mt-3 my-table"
            :closable="false"
          >
            {{ articleGroupStatus }}
          </b-message>
          <APIErrorMessage
            title="Article Group Error"
            :err="articleGroupError"
          />
        </div>
      </div>
    </b-modal>
  </div>
</template>

<script>
import AdvancedOptions from "@/components/AdvancedOptions.vue";
import TagFilters from "@/components/TagFilters.vue";
import PubmedBatchAnalysis from "@/components/PubmedBatchAnalysis.vue";
import FilterSetDisplay from "@/components/FilterSetDisplay.vue";
import FilterSetDisplayBatch from "@/components/FilterSetDisplayBatch.vue";
import ArticleGroupExplorer from "@/components/ArticleGroupExplorer.vue";
import APIErrorMessage from "@/components/APIErrorMessage.vue";
import { pollResource, makeAPIURL } from "@/api";
import { tagObjsToFilterTagIDs } from "@/util";
import isNil from "lodash/isNil";
import groupBy from "lodash/groupBy";
import mapValues from "lodash/mapValues";
import sortBy from "lodash/sortBy";

export default {
  name: "LiteratureMap",
  components: {
    TagFilters,
    PubmedBatchAnalysis,
    AdvancedOptions,
    FilterSetDisplay,
    FilterSetDisplayBatch,
    ArticleGroupExplorer,
    APIErrorMessage,
  },
  data: () => ({
    showModal: false,
    progress: 0,
    driverObj: null,
    articleCount: null,
    showTextSearchInfo: false,
    tagFilters: {},
    advancedOptions: {},
    // Maximum number of articles to process at once.  Set this to a safe number in case
    // the user accidentally runs a very large analysis
    articleLimit: 10000,
    activeParameterTab: 0,
    // If provided by the user, this JSON will be parsed and used directly instead of
    // combining all the other parameters -- see allParams()
    pastedParameterJSON: "{}",
    // Alert the user of errors during the parameter entering process so they can correct them
    paramsErrorMessage: null,
    // Raw defaults for the article group and clustering resources -- these need to be
    // combined before sending to the API (see allParams())
    rawArticleGroupParams: {
      num_terms: 10,
      summary_terms: "named entities",
    },
    rawClusteringParams: {
      umap_seed: 1,
      umap_n_neighbors: 30,
      umap_metric: "cosine",
      umap_min_dist: 0.0,
      hdbscan_min_cluster_size: 3,
      hdbscan_min_samples: 3,
      hdbscan_cluster_selection_epsilon: 0.0,
      hdbscan_do_flat_clustering: false,
      hdbscan_cluster_flattening_epsilon: 0.05,
    },
    filterSetStatus: null,
    filterSetError: null,
    filterSetResult: null,
    clusteringStatus: null,
    clusteringError: null,
    clusteringResult: null,
    articleGroupStatus: null,
    articleGroupError: null,
    articleGroupResult: null,
    articleBatches: null,
    selectedBatchArticles: [],
    selectedBatchQueries: [],
  }),
  computed: {
    articleGroupParams() {
      if (Object.keys(this.advancedOptions).includes("articleGroupParams")) {
        return this.advancedOptions["articleGroupParams"];
      } else {
        return this.rawArticleGroupParams;
      }
    },
    clusteringParams() {
      if (Object.keys(this.advancedOptions).includes("clusteringParams")) {
        return this.advancedOptions["clusteringParams"];
      } else {
        return this.rawClusteringParams;
      }
    },
    allFilterTagIDs() {
      let allFilterTagSelections = this.tagFilters;
      const allFilterTagIDs = tagObjsToFilterTagIDs(allFilterTagSelections);

      return allFilterTagIDs;
    },
    textQuery() {
      //Text query stored in object generated by TagFilters component
      return this.tagFilters["text-query"];
    },
    filterSetParams() {
      // Note this.tagFilters is a Vue observable and doesn't appear to work with ex.
      // lodash's mapValues
      const filterSetParams = {
        filter_tag_ids: this.allFilterTagIDs,
        full_text_search_query: this.textQuery,
        limit: this.articleLimit,
        temp_article_ids: this.selectedBatchArticles,
      };

      return filterSetParams;
    },
    showArticleCount() {
      if (this.articleCount || this.articleCount === 0) {
        return true;
      } else {
        return false;
      }
    },
  },
  watch: {
    advancedOptions: {
      handler() {
        this.getArticleCount(this.allFilterTagIDs, this.textQuery);
      },
      deep: true,
    },
    tagFilters: {
      handler() {
        this.getArticleCount(this.allFilterTagIDs, this.textQuery);
      },
      deep: true,
    },
    clusteringResult(newVal) {
      if (newVal && this.articleGroupResult) {
        this.showModal = false;
        this.scrollToArticleGroupExplorer();
      }
    },
    articleGroupResult(newVal) {
      if (newVal && this.clusteringResult) {
        this.showModal = false;
        this.scrollToArticleGroupExplorer();
      }
    },
  },
  created() {
    this.updateArticleBatches();
  },
  mounted() {},
  methods: {
    updateBatchQueries(query) {
      if (!this.selectedBatchQueries.includes(query)) {
        this.selectedBatchQueries.push(query);
      } else {
        this.selectedBatchQueries.splice(
          this.selectedBatchQueries.indexOf(query),
          1
        );
      }
    },
    articleBatchSearch(selectedBatches) {
      this.selectedBatchArticles = [];
      if (selectedBatches.length > 0) {
        selectedBatches.forEach((selectedBatch) => {
          this.$axios
            .get(makeAPIURL("/literature/pubmed_temp_request_articles"), {
              params: {
                temp_request_id: selectedBatch.temp_request_id,
              },
            })
            .then((res) => {
              this.selectedBatchArticles = this.selectedBatchArticles.concat(
                res.data
              );
              // filter duplicates
              this.selectedBatchArticles = [
                ...new Set(this.selectedBatchArticles),
              ];
            });
        });
      }
    },
    // Assemble all the parameters as required for the API request
    // This properly assimilates the user's choices or the pasted JSON
    // as appropriate -- any code wanting to send requests to the API should
    // deconstruct this object rather than accessing ex. this.filterSetParams
    // directly
    getArticleGroupParams() {
      if (this.activeParameterTab === 0 || this.activeParameterTab == 2) {
        return {
          ...this.articleGroupParams,
          clustering: {
            ...this.clusteringParams,
            filter_set: this.filterSetParams,
          },
        };
      } else {
        try {
          this.paramsErrorMessage = null;
          return JSON.parse(this.pastedParameterJSON);
        } catch (err) {
          this.paramsErrorMessage = err.message;
          return null;
        }
      }
    },
    getClusteringParams() {
      const articleGroupParams = this.getArticleGroupParams();
      if (isNil(articleGroupParams)) {
        return null;
      } else {
        return articleGroupParams.clustering;
      }
    },
    getFilterSetParams() {
      const clusteringParams = this.getClusteringParams();
      if (isNil(clusteringParams)) {
        return null;
      } else {
        return clusteringParams.filter_set;
      }
    },
    getArticleCount(selectedTagIDs, textQuery) {
      if (this.currentRequestCanceller) {
        // Cancel any existing count requests
        this.currentRequestCanceller.cancel();
      }
      if (selectedTagIDs.length > 0 || textQuery) {
        this.articleCountLoading = true;
        this.currentRequestCanceller = this.$axios.CancelToken.source();

        this.$axios
          .get(makeAPIURL("/literature/articles/tags/count"), {
            cancelToken: this.currentRequestCanceller.token,
            params: {
              filter_tag_ids: selectedTagIDs,
              full_text_search_query: textQuery,
            },
          })
          .then((res) => {
            this.currentRequestCanceller = undefined;
            this.articleCountLoading = false;
            this.articleCount = res.data.count;
          })
          .catch((err) => {
            this.articleCountLoading = false;
            this.error = err.message;
          });
      } else {
        this.articleCount = null;
      }
    },
    submit() {
      this.showModal = true;
      const filterSetParams = this.getFilterSetParams();
      this.filterSetResult = null;

      if (isNil(filterSetParams)) {
        this.filterSetStatus = null;
        this.filterSetError = "Unable to determine parameters for filtering.";
        this.updateProgress();
      } else {
        this.filterSetStatus = "Filtering articles...";
        this.filterSetError = null;
        pollResource(makeAPIURL("literature/filter_sets"), filterSetParams)
          .then(({ data }) => {
            this.filterSetStatus = null;
            this.filterSetResult = data;
            this.updateProgress();
          })
          .catch((err) => {
            this.filterSetStatus = null;
            this.filterSetError = err;
            this.updateProgress();
          });
      }

      const clusteringParams = this.getClusteringParams();
      this.clusteringResult = null;
      if (isNil(clusteringParams)) {
        this.clusteringStatus = null;
        this.clusteringError = "Unable to determine parameters for clustering.";
        this.updateProgress();
      } else {
        this.clusteringStatus = "Clustering articles...";
        this.clusteringError = null;
        pollResource(makeAPIURL("literature/clustering"), clusteringParams)
          .then(({ data }) => {
            this.clusteringStatus = null;
            this.clusteringResult = data;
            this.updateProgress();
          })
          .catch((err) => {
            this.clusteringStatus = null;
            this.clusteringError = err;
            this.updateProgress();
          });
      }

      const articleGroupParams = this.getArticleGroupParams();
      this.articleGroupResult = null;
      if (isNil(articleGroupParams)) {
        this.articleGroupStatus = null;
        this.articleGroupError =
          "Unable to determine parameters for article grouping.";
      } else {
        this.articleGroupStatus = "Generating summaries of article groups...";
        this.articleGroupError = null;
        this.updateProgress();
        pollResource(
          makeAPIURL("literature/article_groups"),
          articleGroupParams
        )
          .then(({ data }) => {
            this.articleGroupStatus = null;
            this.articleGroupResult = data;
            this.updateProgress();
          })
          .catch((err) => {
            this.articleGroupStatus = null;
            this.articleGroupError = err;
            this.updateProgress();
          });
      }
    },
    updateArticleBatches() {
      this.articleBatches = null;
      this.$axios
        .get(makeAPIURL("literature/pubmed_temp_requests"))
        .then((res) => {
          this.articleBatches = res.data;
        });
    },
    scrollToArticleGroupExplorer() {
      this.$nextTick(() => {
        this.$refs.articleGroupExplorerSection.scrollIntoView({ behavior: 'smooth' });
      });
    },
    updateProgress() {
      this.progress = 100;
      if (this.filterSetStatus && !this.filterSetError) this.progress -=33;
      if (this.clusteringStatus && !this.clusteringError) this.progress -=33;
      if (this.articleGroupStatus && !this.articleGroupError) this.progress -=34;
    }
  },
};
</script>

<style scoped>
.disable-interaction {
  pointer-events: none;
  opacity: 0.5;
}

.custom-modal {
  background-color: #7957d5;
  /* Ensure the modal only takes up the space it needs */
  max-width: fit-content;
  max-height: fit-content;
  border-radius: 10px;
  margin: auto;
  pointer-events: auto;
}

#status-modal {
  background-color: #a2a0a5;
}

.message {
  background-color: #c9bcee;
}

:deep() .message-header {
  background-color: #7957d5;
}
</style>