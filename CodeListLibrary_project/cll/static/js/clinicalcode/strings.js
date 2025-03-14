import DOMPurify from '../lib/purify.min.js';

/**
 * strictSanitiseString
 * @desc strictly sanitise the given string (remove html, svg, mathML)
 * 
 * @param {string} str
 * 
 * @return {str} The sanitised string 
 */
window.strictSanitiseString = (dirty, opts) => {
  if (isNullOrUndefined(opts)) {
    opts = { html: false, mathMl: false, svg: false, svgFilters: false };
  } else {
    opts = mergeObjects(
      opts,
      { html: false, mathMl: false, svg: false, svgFilters: false },
      true
    );
  }

  dirty = dirty.toString();
  return DOMPurify.sanitize(dirty, { USE_PROFILES: opts });
}

/**
 * interpolateString
 * @desc Interpolate string template
 *       Ref @ https://stackoverflow.com/posts/41015840/revisions
 * 
 * @param {string}      str The string to interpolate
 * @param {object}      params The parameters
 * @param {boolean|any} noSanitise Skip string sanitisation
 * 
 * @return {str} The interpolated string
 * 
 */
window.interpolateString = (str, params, noSanitise) => {
  let names = Object.keys(params);
  let values = Object.values(params);
  if (!noSanitise) {
    names = names.map(x => DOMPurify.sanitize(x));
    values = values.map(x => DOMPurify.sanitize(x));
  }

  return new Function(...names, `return \`${str}\`;`)(...values);
}

/**
 * parseHTMLFromString
 * @desc given a string of HTML, will return a parsed DOM
 * 
 * @param {str}         str        The string to parse as DOM elem
 * @param {boolean|any} noSanitise Skip string sanitisation
 * @param {vararg}      params1    Sanitiser args
 * 
 * @returns {DOM} the parsed html
 */
window.parseHTMLFromString = (str, noSanitise, ...sanitiseArgs) => {
  const parser = new DOMParser();
  if (!noSanitise) {
    str = DOMPurify.sanitize(str, ...sanitiseArgs);
  }

  return parser.parseFromString(str, 'text/html');
}
