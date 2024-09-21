<template>
  <div>
    <h1 class="title">
      Search for an Article
    </h1>
    <b-field label="LitMapper Article ID">
      <b-input
        id="article_search"
        v-model="litmapperArticleID"
        :placeholder="litmapperPlaceholder"
        :disabled="litmapperDisabled"
      />
    </b-field>
    <b-field label="PubMed ID">
      <b-input
        id="PID_search"
        v-model="pmid"
        :placeholder="pmidPlaceholder"
        :disabled="pmidDisabled"
      />
    </b-field>

    <b-button
      id="searchButton"
      @click="searchArticle"
    >
      Search
    </b-button>
    <article
      v-if="error"
      class="message is-danger"
    >
      <div
        class="message-body"
        style="margin-top: 10px"
      >
        {{ error }}
      </div>
    </article>
    <div class="pt-3">
      <ArticleDisplay
        v-if="article"
        :article="article"
      />
    </div>
  </div>
</template>

<script>
import { getArticle } from "@/api";
import ArticleDisplay from "@/components/ArticleDisplay.vue";

export default {
  name: "ArticleSearch",
  components: {
    ArticleDisplay,
  },
  data: () => ({
    error: null,
    article: null,
    litmapperArticleID: "",
    pmid: "",
    driverObj: null,
  }),
  computed: {
    litmapperDisabled() {
      return this.pmid.length > 0;
    },
    pmidDisabled() {
      return this.litmapperArticleID.length > 0;
    },
    pmidPlaceholder() {
      return this.pmidDisabled
        ? "Clear LitMapper Article ID to search by PMID"
        : "Enter PubMed ID";
    },
    litmapperPlaceholder() {
      return this.litmapperDisabled
        ? "Clear PubMed ID to search by LitMapper Article ID"
        : "Enter Article ID";
    },
  },
  mounted() {},
  methods: {
    searchArticle() {
      this.error = null;
      this.article = null;
      const query = this.getSearchParams();
      this.findArticle(query);
    },
    getSearchParams() {
      if (this.litmapperDisabled) {
        return { id: this.pmid, pmid: true };
      } else {
        return { id: this.litmapperArticleID, pmid: false };
      }
    },
    findArticle(searchParams) {
      const articleID = searchParams["id"];
      const usePmid = searchParams["pmid"];

      if (articleID.length > 0) {
        getArticle(articleID, usePmid)
          .then((article) => {
            this.article = article;
          })
          .catch((err) => {
            if (err.response && err.response.status === 404) {
              this.error = "Article with the specified ID doesn't exist.";
            } else {
              this.error = err.message;
            }
          });
      }
    },
  },
};
</script>
