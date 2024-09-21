<template>
  <div>
    <b-loading v-model="loading" />
    <b-message
      v-if="error"
      title="Article Error"
      class="is-danger"
      :closable="false"
    >
      {{ error }}
    </b-message>
    <ArticleDisplay
      v-if="article"
      :article="article"
    />
  </div>
</template>

<script>
import { getArticle } from "@/api";
import ArticleDisplay from "@/components/ArticleDisplay.vue";

export default {
  name: "ArticleView",
  components: {
    ArticleDisplay,
  },
  props: {
    articleID: {
      type: String,
      required: true,
    },
  },
  data: () => ({
    article: null,
    error: null,
    loading: false,
  }),
  mounted() {
    this.loading = true;
    getArticle(this.articleID)
      .then((article) => {
        this.loading = false;
        this.article = article;
      })
      .catch((err) => {
        this.loading = false;
        this.error = err.message;
      });
  },
};
</script>
