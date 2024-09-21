import filter from "lodash/filter";
import keys from "lodash/keys";
import lowerCase from "lodash/lowerCase";
import includes from "lodash/includes";

export const sleep = (ms) => {
  return new Promise((resolve) => setTimeout(resolve, ms));
};

export const textIncludes = (searchText, text) => {
  return includes(lowerCase(text), lowerCase(searchText));
};

export const filterTexts = (matchText, texts) => {
  matchText = lowerCase(matchText);
  return filter(texts, (t) => includes(lowerCase(t), matchText));
};

export const tagObjsToFilterTagIDs = (tagObjs) => {
  // Convert from:
  // { name1: [value1, value2, ...], name2: [valueA, valueB, ...] }
  // to:
  // { filter_tag_ids: [name1value1_id, name1value2_id, name2valueA_id, name2valueB_id, ...] }
  let filterTagIDs = [];
  for (const name of keys(tagObjs)) {
    if (name !== "text-query") {
      const tags = tagObjs[name];
      for (const tag of tags) {
        filterTagIDs.push(tag.tag_id);
      }
    }
  }
  return filterTagIDs;
};
