<template>
  <div class="card">
    <header class="card-header">
      <p class="card-header-title">
        Filter Results
      </p>
    </header>
    <div class="card-content">
      <p class="is-size-4">
        <strong>{{ count }}</strong> {{ countText }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: "FilterSetDisplay",
  props: {
    count: {
      type: Number,
      required: true,
    },
  },
  computed: {
    countText() {
      let countText = "";
      if (this.count < 10000) {
        countText = " articles match selected filters.";
      } else if (this.count > 10000) {
        countText =
          " articles match selected filters. Only first 10,000 articles will be returned.";
      }
      return countText;
    },
  },
};
</script>
