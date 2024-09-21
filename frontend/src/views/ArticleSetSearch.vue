<template>
  <div>
    <b-loading v-model="loading" />
    <b-message
      v-if="error"
      title="Article Set Error"
      class="is-danger"
      :closable="false"
    >
      {{ error }}
    </b-message>
    <div
      v-if="articleSets"
      class="columns"
    >
      <div class="column is-one-quarter">
        <div class="box">
          <h1 class="title is-4">
            Browse Article Sets
          </h1>
          <div>
            <b-field label="Search by Name">
              <b-input v-model="articleSetSearch" />
            </b-field>
          </div>
          <div class="mt-4">
            <p class="has-text-weight-semibold">
              Article Sets
            </p>
            <div
              v-for="articleSet in filteredArticleSets"
              :key="articleSet.article_set_id"
              :class="getArticleSetLevelClasses(articleSet.article_set_id)"
              @click="
                () =>
                  (selectedArticleSetID = articleSet.article_set_id.toString())
              "
            >
              <p class="px-2">
                {{ articleSet.name }}
              </p>
            </div>
          </div>
        </div>
      </div>
      <div class="column">
        <ArticleSet
          v-if="selectedArticleSetID"
          :article-set-i-d="selectedArticleSetID"
          :fetch-article-sets="fetchArticleSets"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { getArticleSets } from "@/api";
import { textIncludes } from "@/util";
import filter from "lodash/filter";
import isNil from "lodash/isNil";
import ArticleSet from "@/views/ArticleSet.vue";

export default {
  name: "ArticleSetSearch",
  components: {
    ArticleSet,
  },
  data: () => ({
    error: null,
    loading: null,
    articleSets: null,
    selectedArticleSetID: null,
    articleSetSearch: "",
  }),
  computed: {
    filteredArticleSets() {
      if (isNil(this.articleSets)) {
        return [];
      }

      return filter(this.articleSets, (a) =>
        textIncludes(this.articleSetSearch, a.name)
      );
    },
  },
  mounted() {
    this.loading = true;
    this.fetchArticleSets();
  },
  methods: {
    getArticleSetLevelClasses(articleSetID) {
      return {
        level: true,
        "article-set-level": true,
        "mb-2": true,
        "py-2": true,
        "active-article-set-level":
          this.selectedArticleSetID === articleSetID.toString(),
      };
    },
    fetchArticleSets() {
      getArticleSets()
        .then((articleSets) => {
          this.loading = false;
          this.articleSets = articleSets;
        })
        .catch((err) => {
          this.loading = false;
          this.error = err.message;
        });
      this.selectedArticleSetID = null;
    },
  },
};
</script>

<style scoped>
.article-set-level {
  cursor: pointer;
}
.article-set-level:hover {
  background-color: lightgray;
}
.active-article-set-level {
  color: white;
  background-color: gray;
}
</style>
