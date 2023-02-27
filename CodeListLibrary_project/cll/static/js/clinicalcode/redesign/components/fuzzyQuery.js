export default class FuzzyQuery {
  static Transformers = {
    IgnoreCase: (s) => {
      return s.toLocaleLowerCase();
    }
  }

  static Results = {
    LIST: 0,
    SORT: 1,
  }

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

  static Distance(haystack, needle) {
    const hlen = haystack.length;
    const nlen = needle.length;
    if (haystack === needle) {
      return 0;
    } else if (!(haystack && needle))  {
      return (haystack || needle).length;
    }

    let i, j;
    let matrix = [];
    for (i = 0; i <= nlen; matrix[i] = [i++]);
    for (j = 0; j <= hlen; matrix[0][j] = j++);

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

  static Search(haystack = [], query = '', sort = 1, transformer = null) {
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
          var score = FuzzyQuery.Distance(item, query);
          results.push({item: item, score: score});
        } else {
          results.push({item: item});
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
