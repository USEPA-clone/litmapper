<template>
  <div>
    <b-button
      class="is-danger"
      :size="`is-${size}`"
      @click="handleRemoveWarningModal"
    >
      <slot />
    </b-button>
    <b-modal
      v-model="removeWarning"
      :destroy-on-hide="false"
      aria-role="dialog"
    >
      <div style="position: relative; left: 20%; max-width: 600px">
        <b-message
          title="This is a permanent action"
          class="is-danger"
          :closable="false"
        >
          <p>Removing an article set cannot be undone:</p>
          <div
            :style="{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '2rem 0rem 0rem 0rem',
            }"
          >
            <b-button @click="remove">
              Remove Article Set
            </b-button>
            <b-button
              class="is-danger"
              @click="closeRemoveWarningModal"
            >
              Cancel
            </b-button>
          </div>
        </b-message>
      </div>
    </b-modal>
  </div>
</template>

<script>
import { makeAPIURL } from "@/api";
export default {
  props: {
    articleSetId: {
      type: Number,
      required: true,
    },
    handleDeleteArticleSet: {
      type: Function,
      required: true,
    },
    size: {
      type: String,
      default: "large",
    },
  },
  data: () => ({
    removeWarning: false,
  }),
  methods: {
    closeRemoveWarningModal() {
      this.removeWarning = false;
    },
    handleRemoveWarningModal() {
      this.removeWarning = true;
    },
    remove() {
      this.$axios
        .create({ validateStatus: () => true })
        .post(makeAPIURL("literature/article_sets/remove"), {
          article_set_id: this.articleSetId,
        })
        .then(() => {
          this.removeWarning = false;
          this.handleDeleteArticleSet();
        });
    },
  },
};
</script>
