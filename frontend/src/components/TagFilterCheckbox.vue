<template>
  <div>
    <b-checkbox
      v-for="tag in tags"
      :key="tag.value"
      v-model="localValue"
      :native-value="tag"
    >
      {{ tag.value }}
    </b-checkbox>
  </div>
</template>

<script>
export default {
  name: "TagFilterCheckbox",
  props: {
    tags: {
      type: Array,
      required: true,
    },
    modelValue: {
      type: Array,
      required: true,
    },
  },
  emits: ["update:modelValue"],
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
  },
};
</script>
