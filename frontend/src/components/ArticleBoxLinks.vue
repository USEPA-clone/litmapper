<template>
  <div class="notification">
    <b-message
      v-if="loading"
      type="is-primary"
      :closable="false"
      :headerless="true"
    >
      {{ "Loading article set..." }}
    </b-message>

    <table
      v-if="!loading"
      class="table"
      :style="{ backgroundColor: 'transparent' }"
    >
      <thead>
        <tr>
          <th><abbr title="Artilce Title">Article Title</abbr></th>
          <th><abbr title="PubMed ID">PMID</abbr></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="article in articlesInfo"
          :key="article['article_id']"
          :style="{ cursor: 'pointer', color: textColors[article.article_id] }"
          @mouseenter="beginHover(article)"
          @mouseleave="endHover()"
          @click="handleClick(article)"
        >
          <td>{{ articleBoxText(article) }}</td>
          <td>{{ article.pmid }}</td>
        </tr>
      </tbody>
    </table>
    <b-modal
      v-model="showArticlePopup"
      :destroy-on-hide="false"
      aria-role="dialog"
    >
      <ArticleDisplay v-bind="{ article: clickedArticle }" />
    </b-modal>
  </div>
</template>

<script>
import { getArticles } from "@/api";
import ArticleDisplay from "@/components/ArticleDisplay.vue";

export default {
  name: "ArticleBoxLinks",
  components: {
    ArticleDisplay,
  },
  props: {
    articleIDs: {
      type: Array,
      required: true,
    },
  },
  data: function () {
    return {
      articlesInfo: null,
      clickedArticle: null,
      hoveredArticle: null,
      showArticlePopup: false,
      loading: true,
    };
  },
  computed: {
    textColors: function () {
      let textColors = {};
      this.articleIDs.forEach((id) => {
        if (this.hoveredArticle && this.hoveredArticle.article_id === id) {
          textColors[id] = "black";
        } else {
          textColors[id] = "#8c67ef";
        }
      });
      return textColors;
    },
  },
  watch: {
    articleIDs: {
      handler(newValue) {
        this.loading = true;
        this.loadArticleInfo(newValue);
      },
      deep: true,
    },
  },
  mounted() {
    this.loadArticleInfo(this.articleIDs);
  },
  methods: {
    articleBoxText: function (article) {
      let title_text = article.title.replace(/\]|\[/g, "");
      if (title_text.length === 0) {
        title_text = article.article_id;
      }
      return String(title_text);
    },
    beginHover: function (article) {
      this.hoveredArticle = article;
    },
    endHover: function () {
      this.hoveredArticle = null;
    },
    handleClick: function (article) {
      this.clickedArticle = article;
      this.showArticlePopup = true;
    },
    loadArticleInfo: function (articleIDs) {
      getArticles(articleIDs).then((articlesInfo) => {
        this.articlesInfo = articlesInfo;
        this.loading = false;
      });
    },
  },
};
</script>
