<template>
  <div>
    <div v-if="showSelector">
      <b-field
        label="Article Set Name"
        class="mb-5"
      >
        <b-input v-model="articleSetName" />
      </b-field>
      <div
        v-for="group in articleGroupsSorted"
        :key="group.id"
        class="level"
      >
        <div class="level-left mr-5">
          <b-field class="level-item">
            <b-checkbox-button
              v-model="articleSetGroupIDs"
              type="is-primary"
              :native-value="group.id"
            >
              {{ getButtonLabel(group.id) }}
            </b-checkbox-button>
          </b-field>
        </div>
        <b-collapse
          class="card level-item"
          animation="slide"
          :model-value="false"
          :style="{ display: 'block', width: '90%' }"
        >
          <template #trigger="props">
            <div
              class="card-header"
              role="button"
            >
              <p class="card-header-title">
                Cluster {{ group.id }}
              </p>
              <p class="card-header-icon">
                <b-icon :icon="props.open ? 'menu-down' : 'menu-up'" />
              </p>
            </div>
          </template>
          <div>
            <ArticleBoxLinks
              :style="{ padding: '10px' }"
              :article-i-ds="group.articleIDs"
            />
          </div>
        </b-collapse>
      </div>
      <div class="has-text-centered">
        <b-button
          class="is-primary"
          size="is-large"
          :disabled="!isCreateAllowed"
          @click="createArticleSet"
        >
          Create Article Set
        </b-button>
      </div>
      <b-loading
        v-model="articleSetLoading"
        :can-cancel="false"
      />
      <hr
        v-if="articleSetResult"
        class="my-5"
      >
      <div
        v-if="articleSetResult"
        class="mt-5"
      >
        <div class="columns is-v-centered">
          <div class="column has-text-centered">
            <div class="level is-mobile">
              <div class="level-left">
                <div class="level-item has-text-centered">
                  <b-field
                    label="Select File Format"
                    class="file-option-select-field"
                  >
                    <b-select v-model="downloadFileFormat">
                      <option
                        v-for="fileFormat in fileFormatOptions"
                        :key="fileFormat.value"
                        :value="fileFormat.value"
                      >
                        {{ fileFormat.text }}
                      </option>
                    </b-select>
                  </b-field>
                </div>
                <div class="level-item">
                  <DownloadFileButton
                    :url="articleSetDownloadURL"
                    :filename="`${articleSetResult.name}.${downloadFileFormat}`"
                    class="ml-5"
                    size="medium"
                    :filetype="downloadFileType"
                    @start="() => (articleSetLoading = true)"
                    @finish="() => (articleSetLoading = false)"
                  >
                    Download Articles ({{ downloadFileFormat.toUpperCase() }})
                  </DownloadFileButton>
                </div>
              </div>
            </div>
          </div>
          <div class="column has-text-centered pt-5">
            <router-link
              :to="{
                name: 'article_set',
                params: { articleSetID: articleSetResult.article_set_id },
              }"
              target="_blank"
            >
              <b-button
                class="is-primary"
                size="is-medium"
              >
                View Article Set
              </b-button>
            </router-link>
          </div>
        </div>
      </div>
      <b-message
        v-if="articleSetError"
        title="Article Set Creation Error"
        class="mt-5 is-danger"
        :closable="false"
      >
        {{ articleSetError }}
      </b-message>
    </div>
    <div
      v-else
      class="mt-3 has-text-centered"
    >
      <p class="subtitle is-5">
        You must select no more than {{ MAX_GROUP_IDS }} clusters to create an
        article set.
      </p>
    </div>
  </div>
</template>

<script>
import size from "lodash/size";
import forEach from "lodash/forEach";
import concat from "lodash/concat";
import isNil from "lodash/isNil";
import { makeAPIURL, makeArticleSetURL } from "@/api";
import ArticleBoxLinks from "@/components/ArticleBoxLinks.vue";
import DownloadFileButton from "@/components/DownloadFileButton.vue";

export default {
  name: "ArticleSetCreator",
  components: {
    ArticleBoxLinks,
    DownloadFileButton,
  },
  props: {
    articleGroups: {
      type: Array,
      required: true,
    },
    articleGroupParams: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      articleSetGroupIDs: [],
      articleSetName: "",
      // Maximum number of group IDs to show the selector elements
      MAX_GROUP_IDS: 10,
      articleSetResult: null,
      articleSetLoading: false,
      articleSetError: null,
      downloadFileFormat: "csv",
      fileFormatOptions: [
        {
          text: "CSV",
          value: "csv",
        },
        {
          text: "RIS",
          value: "ris",
        },
      ],
    };
  },
  computed: {
    articleGroupsSorted() {
      let articleGroups = JSON.parse(JSON.stringify(this.articleGroups));
      function compare(groupA, groupB) {
        return groupA.id > groupB.id ? 1 : -1;
      }
      return articleGroups.sort(compare);
    },
    showSelector() {
      return size(this.articleGroups) <= this.MAX_GROUP_IDS;
    },
    resultsURL() {
      if (isNil(this.articleSetResult)) {
        return "";
      } else {
        return makeAPIURL(
          `/literature/article_set/${this.articleSetResult.article_set_id}/csv`
        );
      }
    },
    isCreateAllowed() {
      return (
        this.articleSetName.length > 0 && this.articleSetGroupIDs.length > 0
      );
    },
    articleSetDownloadURL() {
      return makeAPIURL(
        makeArticleSetURL(
          this.articleSetResult.article_set_id,
          this.downloadFileFormat
        )
      );
    },
    downloadFileType() {
      if (this.downloadFileFormat === "csv") {
        return "text/csv";
      } else {
        return "application/x-research-info-systems";
      }
    },
  },
  methods: {
    getButtonLabel(groupId) {
      return this.articleSetGroupIDs.includes(groupId) ? "Selected" : "Select";
    },

    createArticleSet() {
      this.articleSetResult = null;
      this.articleSetError = null;

      // Get the set of all selected articles, combine them, and push them up to the API
      let selectedArticleIDs = [];
      forEach(this.articleGroups, (group) => {
        if (this.articleSetGroupIDs.includes(group.id)) {
          selectedArticleIDs = concat(selectedArticleIDs, group.articleIDs);
        }
      });

      this.articleSetLoading = true;
      this.$axios
        .create({ validateStatus: () => true })
        .post(makeAPIURL("/literature/article_sets"), {
          article_set: {
            name: this.articleSetName,
            meta_json: this.articleGroupParams,
          },
          article_ids: selectedArticleIDs,
        })
        .then((res) => {
          this.articleSetLoading = false;
          if (res.status === 409) {
            throw new Error("An article set with this name already exists.");
          } else if (res.status === 422) {
            throw new Error("Invalid request parameters.");
          } else if (res.status >= 400) {
            throw new Error(
              `Error creating article set: ${res.status} ${res.statusText}`
            );
          } else {
            this.articleSetResult = res.data;
          }
        })
        .catch((err) => {
          this.articleSetLoading = false;
          this.articleSetError = err.message;
        });
    },
    downloadArticleSetCSV() {
      this.articleSetLoading = true;
    },
  },
};
</script>

<style>
.file-option-select-field * {
  width: 100%;
}
</style>
