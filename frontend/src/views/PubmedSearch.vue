<template>
  <div class="container">
    <h1 class="title">
      LitMapper PubMed Search
    </h1>
    <b-loading
      v-if="pmidArticlesLoading"
      :active="true"
      :can-cancel="false"
    />
    <b-field>
      <template #label>
        Search PubMed Database (Title and Abstract)
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
            You can limit searches to the title and abstract by including "[Title/Abstract]" after keywords. <br>
            You can also use boolean operators like "AND", "OR", and "NOT" for fine-tuning a search. <br>
            For more information on searches, check out the PubMed User Guide <a
              target="_blank"
              style="color: white;"
              href="https://pubmed.ncbi.nlm.nih.gov/help/#narrow-search"
            >(https://pubmed.ncbi.nlm.nih.gov/help/#narrow-search)</a>
          </template>
        </b-tooltip>
      </template>
      <b-input
        v-model="textQuery"
        :placeholder="pubmedPlaceholder"
      />
    </b-field>

    <b-button
      :disabled="pmidArticlesLoading"
      @click="submit"
    >
      Search
    </b-button>

    <section class="py-6">
      <b-message
        v-if="articleCountStatus"
        title="PubMed Search Status"
        class="is-info"
        :closable="false"
      >
        {{ articleCountStatus }}
      </b-message>

      <b-message
        v-if="searchErrorMessage"
        title="Search Error"
        class="is-danger"
        :closable="false"
      >
        {{ searchErrorMessage }}
      </b-message>

      <PubmedFilterSetDisplay
        v-if="showArticleCount"
        :count="articleCount"
        :litmapper-article-count="litmapperArticleCount"
      />

      <b-button
        v-if="showArticleCount"
        class="is-primary mt-4"
        :size="`is-large`"
        :disabled="pmidArticlesLoading"
        @click="addPubmedArticles"
      >
        Add Articles from PubMed
      </b-button>

      <b-message
        v-if="pmidArticlesLoading"
        title="PubMed Articles are Being Fetched"
        class="is-info mt-6"
        :closable="false"
      >
        Please wait several minutes while {{ temp_pmids.length }} articles
        are being stored in the LitMapper database.
      </b-message>

      <b-message
        v-if="pmidArticlesCompleted"
        title="PubMed Article Batch Uploaded into Database"
        class="is-success mt-6"
        :closable="false"
      >
        {{ temp_pmids.length }} articles were successfully uploaded into
        the LitMapper database.
      </b-message>
      <b-message
        v-if="addPubmedArticlesErrorMessage"
        title="Error Adding PubMed Articles"
        class="is-danger mt-6"
        :closable="false"
      >
        {{ addPubmedArticlesErrorMessage }}
      </b-message>
    </section>
  </div>
</template>

<script>
import PubmedFilterSetDisplay from "@/components/PubmedFilterSetDisplay.vue";
import { makeAPIURL } from "@/api";

export default {
  name: "PubmedSearch",
  components: {
    PubmedFilterSetDisplay,
  },
  data: () => ({
    addPubmedArticlesErrorMessage: null,
    articleCount: null,
    articleCountStatus: null,
    litmapperArticleCount: null,
    litmapper_pmids: null,
    temp_pmids: null,
    pmidArticlesLoading: false,
    pmidArticlesCompleted: false,
    searchErrorMessage: null,
    showArticleCount: false,
    showSearchHelpLink: false,
    textQuery: null,
  }),
  computed: {
    pubmedPlaceholder() {
      return "Enter text to search titles and abstracts";
    },
  },
  methods: {
    addPubmedArticles() {
      this.addPubmedArticlesErrorMessage = null;
      this.pmidArticlesLoading = true;
      this.pmidArticlesCompleted = false;
      // temporary for now, will be implemented in the future
      let username = "litmapper-user";
      let password = "password";

      this.$axios
        .create({ validateStatus: () => true })
        .post(makeAPIURL("literature/articles/add_pubmed_ids"), {
          date: new Date().toDateString(),
          password: password,
          litmapper_pmids: this.litmapper_pmids,
          temp_pmids: this.temp_pmids,
          search_query: this.textQuery,
          username: username,
        })
        .then((res) => {
          this.pmidArticlesLoading = false;
          if (res.status === 422) {
            this.addPubmedArticlesErrorMessage =
              "Too many articles requested. Please do not attempt to add more than 2,000 articles.";
          } else {
            this.pmidArticlesCompleted = true;
          }
        })
        .catch((err) => {
          this.pmidArticlesLoading = false;
          this.pmidArticlesCompleted = false;
          this.addPubmedArticlesErrorMessage = err.message;
        });
    },
    submit() {
      this.addPubmedArticlesErrorMessage = null;
      this.pmidArticlesLoading = false;
      this.litmapper_pmids = null;
      this.temp_pmids = null;
      this.pmidArticlesCompleted = false;
      this.searchErrorMessage = null;
      this.showArticleCount = false;
      this.articleCountStatus = "Searching PubMed Database...";
      if (this.textQuery) {
        this.$axios
          .get(makeAPIURL("/literature/articles/tags/pubmed/count"), {
            params: {
              full_text_search_query: this.textQuery,
            },
          })
          .then((res) => {
            this.articleCount = res.data.count;
            this.litmapperArticleCount = res.data.litmapper_count;
            this.litmapper_pmids = res.data.pmids_in_litmapper;
            this.temp_pmids = res.data.pmids_not_in_litmapper;
            this.showArticleCount = true;
            this.articleCountStatus = null;
          })
          .catch((err) => {
            this.searchErrorMessage = err.message;
          });
      } else {
        this.articleCount = null;
      }
    },
  },
};
</script>

<style scoped>
.info-icon {
  margin-left: 1px;
  margin-right: 5px;
}
</style>