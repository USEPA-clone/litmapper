<template>
  <div class="container">
    <h1 class="title">
      LitMapper Article Upload
    </h1>
    <b-loading
      v-if="pmidArticlesLoading"
      :active="true"
      :can-cancel="false"
    />
    <section>
      <b-field
        class="file is-primary"
        :class="{'has-name': !!file}"
      >
        <b-upload
          v-model="file"
          class="file-label"
          accept=".ris, .csv"
          required
          validation-message="Please select a file"
        >
          <span class="file-cta">
            <b-icon
              class="file-icon"
              icon="upload"
            />
            <span class="file-label">Click to upload (Only .ris and .csv)</span>
          </span>
          <span
            v-if="file"
            class="file-name"
          >
            {{ file.name }}
          </span>
        </b-upload>
      </b-field>
    </section>

    <section class="py-6">
      <b-button
        v-if="file"
        class="is-primary mt-4"
        :size="`is-large`"
        :disabled="pmidArticlesLoading"
        @click="addPubmedArticles"
      >
        Add Articles from File
      </b-button>

      <b-message
        v-if="pmidArticlesLoading"
        title="PubMed Articles are Being Fetched"
        class="is-info mt-6"
        :closable="false"
      >
        Please wait several minutes while articles
        are being stored in the LitMapper database.
      </b-message>

      <b-message
        v-if="pmidArticlesCompleted"
        title="PubMed Article Batch Uploaded into Database"
        class="is-success mt-6"
        :closable="false"
      >
        Articles were successfully uploaded into
        the LitMapper database.
      </b-message>
      <b-message
        v-if="addPubmedArticlesErrorMessage"
        title="Error Adding PubMed Articles"
        class="is-danger mt-6"
        :closable="false"
      >
        {{ addPubmedArticlesErrorMessage }}
      </b-message>
    </section>
  </div>
</template>

<script>
import { makeAPIURL } from "@/api";

export default {
  name: "ArticleUpload",
  components: {},
  data: () => ({
    file: null,
    addPubmedArticlesErrorMessage: null,
    pmidArticlesLoading: false,
    pmidArticlesCompleted: false,
  }),
  computed: {},
  methods: {
    addPubmedArticles() {
      this.addPubmedArticlesErrorMessage = null;
      this.pmidArticlesLoading = true;
      this.pmidArticlesCompleted = false;
      // temporary for now, will be implemented in the future
      let username = "litmapper-user";
      let password = "password";

      const formData = new FormData();
      formData.append("file", this.file);
      formData.append("username", username);
      formData.append("password", password);

      this.$axios
        .create({ validateStatus: () => true })
        .post(makeAPIURL("literature/articles/upload"), formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          }
        })
        .then((res) => {
          this.pmidArticlesLoading = false;
          if (res.status === 422) {
            this.addPubmedArticlesErrorMessage =
              "Too many articles requested. Please do not attempt to add more than 2,000 articles.";
          } else if (res.status === 500) {
            this.addPubmedArticlesErrorMessage =
              "Internal server error. Please try again later.";
          } else if (res.status === 400) {
            this.addPubmedArticlesErrorMessage = res.data.detail;
          } else {
            this.file = null;
            this.pmidArticlesCompleted = true;
          }
        })
        .catch((err) => {
          console.error(err);
          this.file = null;
          this.pmidArticlesLoading = false;
          this.pmidArticlesCompleted = false;
          this.addPubmedArticlesErrorMessage = err.message;
        });
    },
  },
};
</script>
