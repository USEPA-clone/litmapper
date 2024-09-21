<template>
  <div>
    <section class="mb-3">
      <div class="columns is-multiline">
        <div />
        <b-field class="column is-half">
          <template #label>
            Full Text Search (Title & Abstract)
            <b-tooltip animated>
              <b-icon
                icon="information"
                size="is-small"
              />
              <template #content>
                <div>
                  <strong>Full Text Search Operators: </strong>
                  <br>The boolean operators <code>AND</code> and <code>OR</code> may be used. 
                  <br>Use the negation operator <code>NOT</code> to exclude articles containing a given string.
                  <br>Use double quotes <code>"exact match"</code> to search for a phrase match. 
                  <br>The default full text search operator is <code>AND</code>.
                </div>
              </template>
            </b-tooltip>
          </template>
          <b-input
            class="pl-0"
            placeholder="Enter text to search titles and abstracts"
            @input="updateTextQuery"
            @focus="showSearchHelpLink = true"
          />
        </b-field>
      </div>
    </section>
  </div>
</template>

<script>
import debounce from "lodash/debounce";
import keys from "lodash/keys";

export default {
  name: "TagFilters",
  props: {
    // Intended for use with v-model
    modelValue: {
      required: true,
    },
    // Object - keys = tag names, values = list of tag values
    tags: {
      required: false,
    },
  },
  emits: ["update:modelValue"],
  data: () => ({
    error: null,
    textSearchShown: false,
    showSearchHelpLink: false,
    showTextSearchHelp: false,
    status: null,
    tagAutocompleteText: {},
    sourceCounts: [],
  }),
  computed: {
    // Propagate v-model (this.modelValue) to the parent
    localValue: {
      get() {
        return this.modelValue;
      },
      set(val) {
        this.$emit("update:modelValue", val);
      },
    },
    textQuery() {
      return this.modelValue["text-query"];
    },
    showTooltips() {
      return this.$store.state.showTooltips;
    },
  },
  methods: {
    updateTextQuery: debounce(function (event) {
      //Request only sent after user has stopped typing for 0.3 seconds.
      this.localValue["text-query"] = event.target._value;
    }, 300),
  },
  beforeMount() {
    // Use Vue.set to add reactivity -- needed for the changes to propagate up the chain
    // properly
    keys(this.tags).forEach((k) => {
      if (this.localValue) {
        this.localValue[k] = [];
      }
    });
  },
};
</script>

<style scoped>
.info-icon {
  margin-left: 5px; /* Adjust this value as needed */
}
strong {
  color: white;
}
</style>