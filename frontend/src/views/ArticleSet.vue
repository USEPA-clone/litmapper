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
    <ArticleSetDisplay
      v-if="articleSet"
      :article-set="articleSet"
      :delete-article-set="deleteArticleSet"
    />
  </div>
</template>

<script>
import { getArticleSetDetail } from "@/api";
import ArticleSetDisplay from "@/components/ArticleSetDisplay.vue";

export default {
  name: "ArticleSet",
  components: {
    ArticleSetDisplay,
  },
  props: {
    articleSetID: {
      type: String,
      required: true,
    },
    fetchArticleSets: {
      type: Function,
      required: true,
    },
  },
  data: () => ({
    articleSet: null,
    loading: false,
    error: null,
  }),
  watch: {
    articleSetID() {
      this.loadArticleSet();
    },
  },
  mounted() {
    this.loadArticleSet();
  },
  methods: {
    loadArticleSet() {
      this.loading = true;
      getArticleSetDetail(this.articleSetID)
        .then((articleSet) => {
          this.loading = false;
          this.articleSet = articleSet;
        })
        .catch((err) => {
          this.loading = false;
          this.error = err.message;
        });
    },
    deleteArticleSet() {
      this.articleSet = null;
      this.fetchArticleSets();
    },
  },
};
</script>
