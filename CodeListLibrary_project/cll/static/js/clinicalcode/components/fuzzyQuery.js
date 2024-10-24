/**
  * @class FuzzyQuery
  * @desc A static class that uses Levenshtein distance to search a haystack.
  * 
  * e.g.
  ```js
    import FuzzyQuery from '../components/fuzzyQuery.js';

    // i.e. some haystack of item(s)
    const haystack = [
      'some_item1',
      'some_item2',
      'another_thing',
      'another_thing_1',
    ];

    // e.g. some search string
    const query = 'some_item';

    // ...attempt to search haystack
    const results = FuzzyQuery.Search(haystack, query, FuzzyQuery.Results.Sort, FuzzyQuery.Transformers.IgnoreCase);
    console.log(results); // --> Of result: ['some_item1', 'some_item2']

  ```
  * 
  */
export default class FuzzyQuery {
  /**
   * @desc transformers are preprocessors that modify both the haystack and the needle prior to fuzzy matching
   */
  static Transformers = {
    IgnoreCase: (s) => {
      return s.toLocaleLowerCase();
    }
  }

  /**
   * @desc enum to det. whether to sort result items by their score or not
   */
  static Results = {
    LIST: 0,
    SORT: 1,
  }

  /**
   * Match
   * @desc a static method to match a needle in a haystack
   * @param {string} haystack the string to match with
   * @param {string} needle the string to compare
   * @return {boolean} a boolean that reflects whether the needle matched the haystack
   */
  static Match(haystack, needle) {
    const hlen = haystack.length;
    const nlen = needle.length;
    if (nlen === hlen) {
      return needle === haystack;
    }

    if (nlen > hlen) {
      return false;
    }

    for (let i = 0, j = 0; i < nlen; i++) {
      var c = needle.charCodeAt(i);
      var p = false;
      while (j < hlen) {
        if (haystack.charCodeAt(j++) === c) {
          p = true;
          break;
        }
      }

      if (p) {
        continue;
      }

      return false;
    }

    return true;
  }

  /**
   * Distance
   * @desc A static method to measure the Levenshtein distance between two strings
   * @param {string} haystack the string to match with
   * @param {string} needle the string to compare
   * @return {number} the distance between the strings
   */
  static Distance(haystack, needle) {
    let nlen = needle.length;
    let hlen = haystack.length;
    if (haystack === needle) {
      return 0;
    } else if (!(haystack && needle))  {
      return (haystack || needle).length;
    }

    if (nlen > hlen) {
      let tmp = hlen;
      hlen = nlen;
      nlen = tmp;

      tmp = haystack;
      haystack = needle;
      needle = tmp;
    }

    let i, j;
    let matrix = Array.from({ length: nlen + 1 }, (_, x) => Array.from({ length: hlen + 1 }, (_, y) => y));
    for (i = 1; i <= nlen; i++) {
      let c = needle.charCodeAt(i - 1);
      for (j = 1; j <= hlen; j++) {
        if (haystack.charCodeAt(j - 1) === c) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(matrix[i - 1][j - 1] + 1, Math.min(matrix[i][j - 1] + 1, matrix[i - 1][j] + 1));
        }
      }
    }

    return matrix[nlen][hlen];
  }

  /**
   * Search
   * @desc A static method to measure the Levenshtein distance between two strings
   * @param {array} haystack An array of haystacks to match with
   * @param {string} query The string to compare
   * @param {number} sort Whether to sort, per the FuzzyQuery.Results enum
   * @param {function} transformer The preprocessing function, per the FuzzyQuery.Transformers enum
   * @return {array} An array of matches
   */
  static Search(haystack, query = '', sort = 1, transformer = null) {
    haystack = haystack || [];
    query = String(query);
    sort = Boolean(sort);

    if (query === '') {
      return haystack;
    }

    if (typeof transformer === 'function') {
      query = transformer(query);
    }

    let results = [];
    for (let i = 0; i < haystack.length; i++) {
      let item = String(haystack[i]);
      if (typeof transformer === 'function') {
        item = transformer(item);
      }
      
      if (FuzzyQuery.Match(item, query)) {
        if (sort) {
          results.push({ item: item, score: FuzzyQuery.Distance(item, query) });
        } else {
          results.push({ item: item });
        }
      }
    }

    if (sort) {
      results.sort((a, b) => {
        if (a.score < b.score) {
          return -1;
        }

        if (a.score > b.score) {
          return 1;
        }

        return 0;
      });
    }

    return results;
  }
}
