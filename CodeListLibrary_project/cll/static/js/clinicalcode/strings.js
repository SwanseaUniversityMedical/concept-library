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
  if (typeof dirty === 'undefined' || dirty === null) {
    return dirty;
  }

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
    names = names.map(x => typeof x === 'string' ? DOMPurify.sanitize(x) : x);
    values = values.map(x => typeof x === 'string' ? DOMPurify.sanitize(x) : x);
  }

  return new Function(...names, `return \`${str}\`;`)(...values);
}

/**
 * pyFormat
 * @desc interpolates a str in a similar fashion to python
 * @note does not support operators
 * 
 * @param {string}           str              the string to be formatted
 * @param {Record<any, any>} params           the parameter lookup
 * @param {boolean}          [sanitise=false] optionally specify whether to sanitise the output; defaults to `false`  
 * 
 * @returns {string} the resulting format string
 */
window.pyFormat = (str, params, sanitise = false) => {
  return str.replace(/{([^{}]+)}/g, (_, param) => {
    let value = param.split('.').reduce((res, x) => res[x], params);
    if (sanitise && typeof value === 'string') {
      value = DOMPurify.sanitize(x);
    }

    return value;
  });
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
  if (!noSanitise) {
    str = DOMPurify.sanitize(str, ...sanitiseArgs);
  }

  const template = document.createElement('template');
  template.innerHTML = str.trim();

  return [...template.content.childNodes].filter(x => isHtmlObject(x));
}

/**
 * composeTemplate
 * @desc Interpolates a `<template />` element
 * 
 * @param {HTMLElement|string} template                 some `<template />` element (or its `string` contents) to interpolate 
 * @param {object}             options                  optionally specify how to interpolate the template
 * @param {object}             options.params           optionally specify a key-value pair describing how to interpolate the `template.innerHTML` content
 * @param {object}             options.modify           optionally specify a key-value pair describing a set of modifcations/alterations to be applied to the resulting output
 * @param {boolean}            options.sanitiseParams   optionally specify whether to sanitise the interpolation parameters; defaults to `false`
 * @param {boolean|Array}      options.sanitiseTemplate optionally specify whether to sanitise and/or how to sanitise the resulting template string; defaults to `true`
 * 
 * @return {HTMLElement[]} the newly interpolated output elements
 */
window.composeTemplate = (template, options) => {
  options = isRecordType(options) ? options : { };
  options = mergeObjects(options, { sanitiseParams: false, sanitiseTemplate: true }, true);

  if (typeof template !== 'string') {
    template = template.innerHTML.trim();
  }

  const params = options.params;
  if (isRecordType(params)) {
    let names = Object.keys(params);
    let values = Object.values(params);
    if (options.sanitiseParams) {
      names = names.map(x => typeof x === 'string' ? DOMPurify.sanitize(x) : x);
      values = values.map(x => typeof x === 'string' ? DOMPurify.sanitize(x) : x);
    }

    template = new Function(...names, `return \`${template}\`;`)(...values);
  }

  const sanitiseTemplate = options.sanitiseTemplate;
  if (Array.isArray(sanitiseTemplate)) {
    template = DOMPurify.sanitize(template, ...sanitiseTemplate);
  } else if (!!sanitiseTemplate) {
    template = DOMPurify.sanitize(template);
  }

  let result = document.createElement('template');
  result.innerHTML = template.trim();

  const parent = options.parent;
  result = [...result.content.childNodes].filter(x => isHtmlObject(x));
  if (isHtmlObject(parent)) {
    for (let i = 0; i < result.length; ++i) {
      result[i] = parent.appendChild(result[i]);
    }
  }

  const render = options.render;
  if (typeof render === 'function') {
    const res = render(result);
    if (Array.isArray(res)) {
      result = res;
    }
  }

  const mods = options.modify;
  if (!Array.isArray(mods)) {
    return result;
  }

  let mod, sel, obj;
  for (let i = 0; i < mods.length; ++i) {
    mod = mods[i];
    sel = mod.select;
    if (!stringHasChars(sel)) {
      continue;
    }

    const apply = typeof mod.apply === 'function' ? mod.apply : null;
    const parent = isHtmlObject(mod.parent) ? mod.parent : null;
    for (let j = 0; j < result.length; ++j) {
      obj = result[j];
      if (!obj.matches(sel)) {
        continue;
      }

      if (parent) {
        obj = parent.appendChild(obj);
        result[j] = obj;
      }

      if (apply) {
        const res = apply(obj, mod);
        if (!!res && isHtmlObject(res)) {
          obj = res;
          result[j] = obj;
        }
      }
    }
  }

  return result;
}
