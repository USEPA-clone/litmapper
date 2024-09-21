<template>
  <b-taginput
    v-model="localValue"
    autocomplete
    :data="autocompleteTags"
    :open-on-focus="true"
    field="value"
    icon="magnify"
    placeholder="Choose one or more options"
    clearable
    @typing="setAutocompleteText"
    @input="clearAutocompleteText"
  />
</template>

<script>
import { textIncludes } from "@/util";
import filter from "lodash/filter";

export default {
  name: "TagFilterAutocomplete",
  props: {
    tags: {
      required: true,
    },
    modelValue: {
      required: true,
    },
  },
  emits: ["update:modelValue"],
  data: () => ({
    autocompleteText: "",
  }),
  computed: {
    autocompleteTags() {
      return filter(this.tags, (t) =>
        textIncludes(this.autocompleteText, t.modelValue)
      );
    },
    // Propagate v-model (this.modelValue) to the parent
    localValue: {
      get() {
        return this.modelValue;
      },
      set(val) {
        this.$emit("update:modelValue", val);
      },
    },
  },
  methods: {
    setAutocompleteText(text) {
      this.autocompleteText = text;
    },
    clearAutocompleteText() {
      this.autocompleteText = "";
    },
  },
};
</script>
