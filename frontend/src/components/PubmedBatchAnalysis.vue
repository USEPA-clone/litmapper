<template>
  <div>
    <section class="mb-3">
      <p class="mb-3">
        Use this tab to select a batch of articles and perform analysis on
        articles retrieved from the
        <router-link to="/pubmed-search">
          PubMed Search
        </router-link>. In
        addition, you may combine the analysis with articles filtered through
        the Select Parameters tab.
      </p>
      <hr>
      <table
        class="table w-100"
        :style="{ backgroundColor: 'transparent' }"
      >
        <thead>
          <tr>
            <th><abbr title="Query Information">Query Text</abbr></th>
            <th><abbr title="Date">Date</abbr></th>
            <th><abbr title="Requester">Requester</abbr></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="batch in articleBatches"
            :key="batch.name"
            :value="batch"
            :class="
              selectedArticleBatches.includes(batch)
                ? 'batch-row selected'
                : 'batch-row'
            "
            @click="handleTableBatchSelection(batch)"
          >
            <th>{{ batch.search_query }}</th>
            <th>{{ batch.date }}</th>
            <th class="end-column">
              {{ batch.requester }}
              <button
                v-if="selectedArticleBatches.includes(batch)"
                class="remove-batch"
                @click="handleRemoveWarningModal(batch)"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  fill="currentColor"
                  class="bi bi-trash"
                  viewBox="0 0 16 16"
                >
                  <path
                    d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"
                  />
                  <path
                    fill-rule="evenodd"
                    d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"
                  />
                </svg>
              </button>
            </th>
          </tr>
        </tbody>
      </table>
      <b-modal
        v-model="removeWarning"
        :destroy-on-hide="false"
        aria-role="dialog"
      >
        <div style="position: relative; left: 20%; max-width: 600px">
          <b-message
            title="This is a permanent action"
            class="is-danger"
            :closable="false"
          >
            <p>
              Removing a temporary article batch and its articles cannot be
              undone:
            </p>
            <div
              :style="{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '2rem 0rem 0rem 0rem',
              }"
            >
              <b-button @click="removeArticleBatch">
                Remove Article Batch
              </b-button>
              <b-button
                class="is-danger"
                @click="closeRemoveWarningModal"
              >
                Cancel
              </b-button>
            </div>
          </b-message>
        </div>
      </b-modal>
      <b-loading
        v-model="currentlyRemoving"
        :can-cancel="false"
      />
    </section>
  </div>
</template>

<script>
import { makeAPIURL } from "@/api";
import { tagObjsToFilterTagIDs } from "@/util";
import debounce from "lodash/debounce";
import keys from "lodash/keys";

export default {
  name: "PubmedBatchAnalysis",
  props: {
    // Intended for use with v-model
    modelValue: {
      required: true,
    },
    // Object - keys = tag names, values = list of tag values
    tags: {
      required: false,
    },
    articleBatches: {
      required: true,
    },
    articleBatchSearch: {
      required: true,
    },
    selectedBatchArticles: {
      required: true,
    },
    updateArticleBatches: {
      required: true,
    },
    updateBatchQueries: {
      required: true,
    },
  },
  emits: ["update:modelValue"],
  data: () => ({
    error: null,
    hoveredArticleBatch: null,
    selectedArticleBatches: [],
    status: null,
    textSearchShown: false,
    showSearchHelpLink: false,
    showTextSearchHelp: false,
    filterParamsShown: false,
    tagAutocompleteText: {},
    tagCheckboxes: {},
    tagAutocompletes: {},
    tagFilterLabels: {
      source: "Source",
      endpoint: "Endpoint (January 2020)",
      "article-type": "Article Type",
      "evidence-stream": "Evidence Stream (January 2020)",
      "endpoint-pilot2": "Key MIE or Target Mechanism",
      "evidence-stream-pilot3": "Evidence Stream (Animal/In Vitro)",
    },
    currentRemoveBatch: null,
    removeWarning: false,
    currentlyRemoving: false,
  }),
  computed: {
    // Propagate v-model (this.modelValue) to the parent
    localValue: {
      get() {
        return this.modelValue;
      },
      set(val) {
        this.$emit("update:modelValue", val);
      },
    },
    filterTagIDs() {
      //Used for heatmap. Remove if heatmap.
      return tagObjsToFilterTagIDs(this.modelValue);
    },
  },
  watch: {
    selectedArticleBatches() {
      this.articleBatchSearch(this.selectedArticleBatches);
    },
  },
  methods: {
    beginHover: function (batch) {
      this.hoveredArticleBatch = batch;
    },
    endHover: function () {
      this.hoveredArticleBatch = null;
    },
    updateTagSelection(event, tagName) {
      this.localValue[tagName] = event;
    },
    updateTextQuery: debounce(function (event) {
      //Request only sent after user has stopped typing for 0.3 seconds.
      this.localValue["text-query"] = event;
    }, 300),
    handleTableBatchSelection: function (batch) {
      if (this.selectedArticleBatches.includes(batch)) {
        this.selectedArticleBatches.splice(
          this.selectedArticleBatches.indexOf(batch),
          1
        );
      } else {
        this.selectedArticleBatches.push(batch);
      }
      this.updateBatchQueries(batch.search_query);
    },
    closeRemoveWarningModal() {
      this.removeWarning = false;
    },
    handleRemoveWarningModal(batch) {
      this.currentRemoveBatch = batch;
      this.removeWarning = true;
    },
    removeArticleBatch: function () {
      this.currentlyRemoving = true;
      this.$axios
        .create({ validateStatus: () => true })
        .post(makeAPIURL("literature/pubmed_temp_requests/remove"), {
          article_batch_id: this.currentRemoveBatch.temp_request_id,
        })
        .then(() => {
          this.selectedArticleBatches.splice(
            this.selectedArticleBatches.indexOf(
              this.currentRemoveBatch.temp_request_id
            ),
            1
          );
          this.currentlyRemoving = false;
          this.removeWarning = false;
          this.updateArticleBatches();
        });
    },
  },
  beforeMount() {
    // Use Vue.set to add reactivity -- needed for the changes to propagate up the chain
    // properly
    keys(this.tags).forEach((k) => (this.localValue[k] = []));
  },
};
</script>

<style scoped>
.batch-row.selected {
  background-color: #8c67ef;
  color: white;
}
.batch-row {
  cursor: pointer;
  color: #4a4a4a;
}
.batch-row:hover:not(.selected) {
  background-color: rgba(204, 198, 198, 0.466);
}
.end-column {
  margin-bottom: -1px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.remove-batch {
  display: flex;
  align-items: center;
  background-color: transparent;
  color: white;
  border: none;
  cursor: pointer;
}
.table abbr {
  font-weight: bold;
  text-decoration: none;
}
.table th {
  font-weight: normal;
  color: inherit;
  padding: 15px;
}
.table {
  margin: 0 auto;
  position: relative;
}
tbody {
  display: block;
  overflow: auto;
  max-height: 350px;
}
thead,
tbody tr,
tfoot {
  display: table;
  width: 100%;
  table-layout: fixed; /* even columns width , fix width of table too*/
}
</style>
