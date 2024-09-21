<template>
  <div class="box">
    <div class="content">
      <p class="is-size-4 has-text-weight-bold">
        {{ article.title }}
      </p>
      <div class="columns is-size-6 my-1">
        <p class="column">
          <span class="has-text-weight-bold">LitMapper Article ID:&nbsp;</span><span class="has-text-grey">{{ article.article_id }}</span>
        </p>
        <p class="column">
          <span class="has-text-weight-bold">PMID:&nbsp;</span><span class="has-text-grey"> {{ article.pmid }}</span>
        </p>
        <p class="column">
          <span class="has-text-weight-bold">Published:&nbsp;</span><span class="has-text-grey">
            {{ article.publication_date }}</span>
        </p>
      </div>
      <p class="has-text-weight-bold">
        Tags
      </p>
      <b-field
        grouped
        group-multiline
      >
        <div
          v-for="tag in article.tags"
          :key="tag.value + '-' + tag.name"
          class="control"
        >
          <article-generic-tag :tag="tag" />
        </div>
      </b-field>
      <p class="has-text-weight-bold mt-3">
        MeSH Terms
      </p>
      <b-field
        grouped
        group-multiline
      >
        <div
          v-for="meshTerm in article.mesh_terms"
          :key="meshTerm.name"
          class="control"
        >
          <b-tag>{{ meshTerm.name }}</b-tag>
        </div>
      </b-field>
      <hr class="my-2">
      <p class="has-text-weight-bold">
        Abstract
      </p>
      <p class="is-size-10">
        {{ article.abstract }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: "ArticleDisplay",
  props: {
    article: {
      type: Object,
      required: true,
    },
  },
};
</script>
