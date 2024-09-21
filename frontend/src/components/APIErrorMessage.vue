<template>
  <b-message
    v-if="err"
    :title="title"
    class="is-danger"
    :closable="false"
  >
    <p>{{ err.message }}</p>
    <pre
      v-if="err.response"
      class="mt-3"
    >{{ err.response.data }}</pre>
  </b-message>
</template>

<script>
export default {
  name: "APIErrorMessage",
  props: {
    err: {
      type: Object,
    },
    title: {
      type: String,
      default: "Error",
    },
  },
};
</script>
