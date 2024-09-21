<template>
  <div class="card">
    <header class="card-header">
      <p class="card-header-title">
        Search Results
      </p>
    </header>
    <div class="card-content">
      <p class="is-size-4">
        <strong>{{ count }}</strong> articles match search in Pubmed.
      </p>
      <p class="is-size-6 py-2">
        {{ searchResultsText }}
      </p>
    </div>
  </div>
</template>

<script>
import round from "lodash/round";

export default {
  name: "PubmedFilterSetDisplay",
  props: {
    count: {
      type: Number,
      required: true,
    },
    litmapperArticleCount: {
      type: Number,
      required: true,
    },
  },
  computed: {
    searchResultsText() {
      if (this.count >= 100000) {
        return "Please enter a more specific query to calculate LitMapper statistics (less than 100,000 Pubmed results.)";
      } else {
        return `${this.litmapperArticleCount} ${this.countFraction} ${this.articleText}`;
      }
    },
    articleText() {
      if (this.litmapperArticleCount === 1) {
        return "of these articles is in the LitMapper database.";
      } else {
        return "of these articles are in the LitMapper database.";
      }
    },
    countFraction() {
      if (this.count && this.litmapperArticleCount) {
        return `(${round((this.litmapperArticleCount / this.count) * 100, 2)}%)`;
      } else {
        return "(0%)";
      }
    },
  },
};
</script>
