<template>
  <b-button
    class="is-primary"
    :size="`is-${size}`"
    @click="download"
  >
    <slot />
  </b-button>
</template>

<script>
export default {
  props: {
    url: {
      type: String,
      required: true,
    },
    filename: {
      type: String,
      required: true,
    },
    filetype: {
      type: String,
      required: true,
    },
    size: {
      type: String,
      default: "medium",
    },
  },
  methods: {
    download() {
      this.$emit("start");
      this.$axios
        .get(this.url)
        .then((res) => {
          this.$emit("finish");
          const blob = new Blob([res.data], { type: this.filetype });
          const link = document.createElement("a");
          link.href = window.URL.createObjectURL(blob);
          link.download = this.filename;
          link.click();
        })
        .catch((err) => {
          this.$emit("finish");
          this.$emit("error", err);
        });
    },
  },
};
</script>
