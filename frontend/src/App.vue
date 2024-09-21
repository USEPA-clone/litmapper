<template>
  <section class="section">
    <b-navbar :shadow="true">
      <template #start>
        <b-navbar-item
          tag="router-link"
          to="/articles"
        >
          Search Articles
        </b-navbar-item>
        <b-navbar-item
          tag="router-link"
          to="/literature-map"
        >
          Literature Map
        </b-navbar-item>
        <b-navbar-item
          tag="router-link"
          to="/pubmed-search"
        >
          PubMed Search
        </b-navbar-item>
        <b-navbar-item
          tag="router-link"
          to="/article-upload"
        >
          Article Upload
        </b-navbar-item>
        <b-navbar-item
          tag="router-link"
          to="/article-sets"
        >
          Browse Article Sets
        </b-navbar-item>
      </template>
    </b-navbar>
    <div class="container mt-5">
      <router-view />
    </div>
  </section>
</template>

<style>
.active-tab {
  text-decoration: underline;
  text-decoration-color: #7957d5;
}
</style>
