import $axios from "axios";
import startsWith from "lodash/startsWith";
import { sleep } from "@/util";

export const axios = $axios;

export const makeAPIURL = (path) => {
  let startChar = "";
  if (!startsWith(path, "/")) {
    startChar = "/";
  }
  return `/api${startChar}${path}`;
};

export const poll = async (
  promiseFactory,
  responseCallback,
  retries = Infinity,
  timeout = 1000
) => {
  // Call the factory to create and run a new promise at intervals, calling the given callback
  // on the response each time.
  // If the callback returns something non-null, the poll resolves.  If it returns null, the poll
  // continues.
  // If it throws an exception, the promise throws.
  // Avoid using recursion to avoid filling up the browser's call stack on long-running polls.
  let curRetry = retries;
  do {
    const responseVal = responseCallback(await promiseFactory());
    if (responseVal) {
      return responseVal;
    } else {
      curRetry--;
    }
    await sleep(timeout);
  } while (curRetry >= 0);
};

export const pollResource = (resourceURL, resourceParams) => {
  // Return a promise which posts a creation request to the given resource URL,
  // polls for job status, and resolves with the data for the resource if successful -- otherwise,
  // throws an exception
  // Don't let axios throw on error codes >= 400 so we can add a more helpful error message
  // below.
  return $axios
    .create({ validateStatus: () => true })
    .post(resourceURL, resourceParams)
    .then((res) => {
      // First make sure the job is created successfully and poll until it's finished.
      // NOTE: A finished job does NOT necessarily mean the resource is created, since
      // a job will return as finished if another job is currently running to create the
      // same resource.
      if (res.status === 202) {
        const jobURL = makeAPIURL(res.headers.location);
        const promiseFactory = () => $axios.get(jobURL);
        const responseCallback = (res) => {
          const job = res.data;
          if (job.status === "success") {
            return job.result_url;
          } else if (job.status === "failed") {
            let err = new Error(job.status_detail);
            err.response = res;
            throw err;
          } else {
            return null;
          }
        };
        return poll(promiseFactory, responseCallback);
      } else {
        let err = new Error(
          `Error querying ${resourceURL}: ${res.status} ${res.statusText}`
        );
        err.response = res;
        throw err;
      }
    })
    .then((resultURL) => {
      // Now attempt to retrieve the resource.  Here we may need to poll again until
      // the resource exists if another job is currently creating it (from another user
      // or a previous submission on the same page).
      const resultAPIURL = makeAPIURL(resultURL);
      // We expect 404s if the resource doesn't exist yet, so don't allow axios to throw on a 404.
      const promiseFactory = () =>
        $axios.create({ validateStatus: () => true }).get(resultAPIURL);
      const responseCallback = (res) => {
        if (res.status === 404 || res.status === 409) {
          // The resource doesn't exist yet -- hopefully another job is creating it
          // Keep polling
          return null;
        } else if (res.status >= 200 && res.status < 300) {
          return { resultURL: resultURL, data: res.data };
        } else {
          let err = new Error(
            `Error querying ${resultAPIURL}: ${res.status} ${res.statusText}`
          );
          err.response = res;
          throw err;
        }
      };
      return poll(promiseFactory, responseCallback);
    });
};

export const getArticle = (articleID, pmid = false) => {
  const query = pmid === true ? `pmid=${articleID}` : `article_id=${articleID}`;
  return $axios.get(makeAPIURL(`literature/article?${query}`)).then((res) => {
    return res.data;
  });
};

export const getArticles = (articleIDs) => {
  let articlesQueryString = "";
  articleIDs.forEach((id) => {
    articlesQueryString += `article_ids=${id}&`;
  });
  return $axios
    .get(makeAPIURL(`literature/articles?${articlesQueryString}`))
    .then((res) => {
      return res.data;
    });
};

export const getArticleSetDetail = (articleSetID) => {
  return $axios
    .get(makeAPIURL(`literature/article_set/${articleSetID}`))
    .then((res) => {
      return res.data;
    });
};

export const getArticleSets = () => {
  return $axios.get(makeAPIURL("literature/article_sets")).then((res) => {
    return res.data;
  });
};

export const makeArticleSetURL = (articleSetID, fileType) => {
  return `/literature/article_set/${articleSetID}/${fileType}`;
};
