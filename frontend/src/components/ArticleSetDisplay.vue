<template>
  <div
    v-if="!removed"
    class="box"
  >
    <b-loading v-model="loading" />
    <h1 class="title">
      Article Set: {{ articleSet.name }}
    </h1>
    <div class="level">
      <div class="level-left">
        <div class="level-item">
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
            :url="downloadURL"
            :filename="`${articleSet.name}.${downloadFileFormat}`"
            class="ml-5"
            size="medium"
            :filetype="downloadFileType"
            @start="downloadStart"
            @finish="downloadEnd"
          >
            Download Articles ({{ downloadFileFormat.toUpperCase() }})
          </DownloadFileButton>
        </div>
      </div>
    </div>
    <h3 class="subtitle">
      Articles
    </h3>
    <div class="mb-5">
      <ArticleBoxLinks :article-i-ds="articleIDs" />
    </div>
    <div>
      <tree-view
        :data="articleSet.meta_json"
        :options="{
          rootObjectKey: 'Metadata',
          maxDepth: 4,
        }"
      />
    </div>
    <hr>
    <RemoveSetButton
      :article-set-id="articleSetId"
      :handle-delete-article-set="handleDeleteArticleSet"
      size="medium"
    >
      Remove Article Set
    </RemoveSetButton>
  </div>
</template>

<script>
import { makeAPIURL, makeArticleSetURL } from "@/api";
import ArticleBoxLinks from "@/components/ArticleBoxLinks.vue";
import DownloadFileButton from "@/components/DownloadFileButton.vue";
import RemoveSetButton from "@/components/RemoveSetButton.vue";
import map from "lodash/map";
import sortBy from "lodash/sortBy";

export default {
  name: "ArticleSetDisplay",
  components: {
    DownloadFileButton,
    ArticleBoxLinks,
    RemoveSetButton,
  },
  props: {
    articleSet: {
      type: Object,
      required: true,
    },
    deleteArticleSet: {
      type: Function,
      required: true,
    },
  },
  data: () => ({
    loading: false,
    removed: false,
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
  }),
  computed: {
    articleIDs() {
      return sortBy(map(this.articleSet.articles, (a) => a.article_id));
    },
    articleSetId() {
      return this.articleSet.article_set_id;
    },
    downloadURL() {
      return makeAPIURL(
        makeArticleSetURL(
          this.articleSet.article_set_id,
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
    downloadStart() {
      this.loading = true;
    },
    downloadEnd() {
      this.loading = false;
    },
    handleDeleteArticleSet() {
      this.deleteArticleSet();
      this.removed = true;
    },
  },
};
</script>

<style>
.file-option-select-field * {
  width: 100%;
}
</style>
