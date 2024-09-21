<template>
  <div class="card">
    <header class="card-header">
      <p class="card-header-title">
        Article Batch Content
      </p>
    </header>
    <div class="card-content">
      <p class="is-size-4">
        <strong>{{ count }}</strong> {{ count === 1 ? "article" : "articles" }}
        {{ countText }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: "FilterSetDisplayBatch",
  props: {
    count: {
      type: Number,
      required: true,
    },
    batchQueries: {
      type: Array,
      required: true,
    },
  },
  computed: {
    countText() {
      if (this.batchQueries.length > 1) {
        return (
          "included from " +
          this.batchQueries.length +
          " temporary PubMed batches"
        );
      } else {
        return 'included from batch with query "' + this.batchQueries[0] + '"';
      }
    },
  },
};
</script>
