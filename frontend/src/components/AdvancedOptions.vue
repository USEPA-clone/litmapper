<template>
  <div>
    <b-collapse
      v-model:model-value="advancedOptionsShown"
      class="panel mt-5"
      animation="slide"
    >
      <template #trigger>
        <div
          class="panel-heading"
          role="button"
        >
          <strong>Advanced Options</strong>
          <b-tooltip animated>
            <b-icon
              icon="information"
              size="is-small"
              class="info-icon"
            />
            <template #content>
              Use these advance options to filter and cluster the articles.
            </template>
          </b-tooltip>
          <b-icon
            :icon="advancedOptionsCaret"
            size="is-small"
            aria-hidden="true"
          />
        </div>
      </template>
      <div class="panel-block">
        <div class="columns mt-2 ml-2 mr-2 is-multiline">
          <p class="text-bold column is-12 has-text-weight-bold">
            Advanced Clustering Settings
          </p>
          <b-tooltip
            animated
            :close-delay="2000"
          >
            <b-icon
              icon="information"
              size="is-small"
              class="info-icon"
            />
            <template #content>
              <ul>
                <li>
                  - UMAP params: <a
                    target="_blank"
                    style="color: white;"
                    href="https://umap-learn.readthedocs.io/en/latest/parameters.html#"
                  >https://umap-learn.readthedocs.io/en/latest/parameters.html#</a>
                </li>
                <li>
                  - HDBSCAN params: <a
                    target="_blank"
                    style="color: white;"
                    href="https://hdbscan.readthedocs.io/en/latest/parameter_selection.html"
                  >https://hdbscan.readthedocs.io/en/latest/parameter_selection.html</a>
                </li>
              </ul>
            </template>
          </b-tooltip>
          <tree-view
            class="mb-5"
            style="font-size: 1 rem"
            :data="clusteringParams"
            :options="{
              modifiable: true,
              rootObjectKey: 'Clustering Params',
            }"
            @change-data="updateClusteringParams"
          />
          <b-tooltip animated>
            <b-icon
              icon="information"
              size="is-small"
              class="info-icon"
            />
            <template #content>
              <ul>
                <li>- num_terms: The total number of terms to show in the Cluster Heatmap</li>
                <li>- summary_terms: "named entities" or "mesh terms"</li>
              </ul>
            </template>
          </b-tooltip>
          <tree-view
            class="mb-5"
            :data="articleGroupParams"
            :options="{
              modifiable: true,
              rootObjectKey: 'Article Group Params',
            }"
            @change-data="updateArticleGroupParams"
          />
        </div>
      </div>
    </b-collapse>
  </div>
</template>

<script>
import TagFilterAutocomplete from "@/components/TagFilterAutocomplete.vue";
import debounce from "lodash/debounce";
import startCase from "lodash/startCase";
import keys from "lodash/keys";

export default {
  name: "AdvancedOptions",
  components: {
    TagFilterAutocomplete,
  },
  props: {
    // Intended for use with v-model
    modelValue: {
      type: Object,
      required: true,
    },
    articleGroupParams: {
      type: Object,
      required: true,
    },
    clusteringParams: {
      type: Object,
      required: true,
    },
  },
  emits: ["update:modelValue"],
  data: () => ({
    error: null,
    showTextSearchInfo: false,
    status: null,
    tagCheckboxes: {},
    tagAutocompletes: {},
    articleCount: null,
    advancedOptionsShown: false,
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
    articleCountText() {
      let articleCountText = "";
      if (this.articleCount !== null && this.articleCount >= 0) {
        articleCountText =
          String(this.articleCount) + " Articles Currently Match Filters";
      }
      return articleCountText;
    },
    advancedOptionsCaret() {
      return this.advancedOptionsShown ? "chevron-up" : "chevron-down";
    },
  },
  methods: {
    handleTextInfoHover() {
      this.showTextSearchInfo = true;
    },
    updateTagSelection(event, tagName) {
      this.localValue[tagName] = event;
    },
    updateTextQuery: debounce(function (event) {
      //Request only sent after user has stopped typing for 0.3 seconds.
      this.localValue["text-query"] = event;
    }, 300),
    updateClusteringParams(event) {
      this.localValue["clusteringParams"] = event;
    },
    updateArticleGroupParams(event) {
      this.localValue["articleGroupParams"] = event;
    },
    convertToLabel(rawText) {
      return startCase(rawText);
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
.info-icon {
  margin-left: 5px;
  margin-right: 5px;
}
</style>