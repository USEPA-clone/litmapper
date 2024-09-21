import { createWebHashHistory, createRouter } from "vue-router";
import Article from "../views/ArticleView.vue";
import ArticleSet from "../views/ArticleSet.vue";
import ArticleSearch from "../views/ArticleSearch.vue";
import ArticleSetSearch from "../views/ArticleSetSearch.vue";
import LiteratureMap from "../views/LiteratureMap.vue";
import PubmedSearch from "../views/PubmedSearch.vue";
import ArticleUpload from "../views/ArticleUpload.vue";

const routes = [
  {
    path: "/article/:articleID",
    name: "article",
    props: true,
    component: Article,
  },
  {
    path: "/articles",
    alias: "/",
    name: "articles",
    component: ArticleSearch,
  },
  {
    path: "/article-set/:articleSetID",
    name: "article_set",
    props: true,
    component: ArticleSet,
  },
  {
    path: "/article-sets/",
    name: "article_sets",
    component: ArticleSetSearch,
  },
  {
    path: "/literature-map",
    name: "literature_map",
    component: LiteratureMap,
  },
  {
    path: "/pubmed-search",
    name: "pubmed_search",
    component: PubmedSearch,
  },
  {
    path: "/article-upload",
    name: "article_upload",
    component: ArticleUpload,
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  linkActiveClass: "active-tab",
});

export default router;
