import { createApp } from "vue";

import ECharts from "vue-echarts";
import qs from "qs";
import Buefy from "buefy";
import App from "./App.vue";
import router from "./router";
import { TreeView } from "vue3-json-tree-view";
import { axios } from "./api";
// import "bulma/css/bulma.css";
import "buefy/dist/buefy.css";
import "@mdi/font/css/materialdesignicons.css";

const app = createApp(App);

app.component("TreeView", TreeView);
app.component("VChart", ECharts);
app.use(Buefy);

// Needed to make axios play nicely with FastAPI --
// https://github.com/tiangolo/fastapi/issues/739
// By default, axios sends parameter arrays like: param[]=1&param[]=2
// But FastAPI is hardcoded to expect: param=1&param=2
// Use the qs library to convert to the FastAPI format
axios.defaults.paramsSerializer = (params) =>
  qs.stringify(params, { indices: false });
app.config.globalProperties.$axios = axios;

app.use(router);
app.mount("#app");
