/**
 * CLU_TRANSITION_METHODS
 * @desc defines the transition methods associated
 *       with the animation of an element
 * 
 */
const CLU_TRANSITION_METHODS = {
  'transition': 'transitionend',
  'WebkitTransition': 'webkitTransitionEnd',
  'OTransition': 'oTransitionEnd otransitionend',
  'MozTransition': 'mozTransitionEnd',
};

/**
 * CLU_DOI_PATTERN
 * @desc Regex pattern to match DOI
 */
const CLU_DOI_PATTERN = /\b(10[.][0-9]{4,}(?:[.][0-9]+)*\/(?:(?![\"&\'<>])\S)+)\b/gm;

/**
  * deepCopy
  * @desc Performs a deep clone of the object i.e. recursive clone
  * @param {object} obj The object to clone
  * @returns {object} The cloned object
  */
const deepCopy = (obj) => {
  return structuredClone(obj); // JSON.parse(JSON.stringify(obj));
}

/**
  * mergeObjects
  * @desc Merges two objects together where the first object takes precedence (i.e., it's not overriden)
  * @param {object} a An object to clone that takes precedence
  * @param {object} b The object to clone and merge into the first object
  * @returns {object} The merged object
  */
const mergeObjects = (a, b) => {
  Object.keys(b).forEach(key => {
    if (!(key in a))
      a[key] = b[key];
  });

  return a;
}

/**
 * generateUUID
 * @desc Generates a UUID
 *       Ref @ https://en.wikipedia.org/wiki/Universally_unique_identifier
 * 
 * @returns {string} a UUID
 */
const generateUUID = () => {
  let dt = new Date().getTime();
  return ('xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx').replace(/[xy]/g, (char) => {
    const r = (dt + Math.random() * 16) % 16 | 0;
    dt = Math.floor(dt / 16);
    return (char == 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

/**
  * getTransitionMethod
  * @desc Finds the relevant transition method of the explorer
  * @returns {object} The transition method
  */
const getTransitionMethod = () => {
  const root = document.documentElement;
  for (let method in CLU_TRANSITION_METHODS) {
    if (typeof root.style[method] !== 'undefined') {
      return CLU_TRANSITION_METHODS[method];
    }
  }

  return undefined;
}

/**
  * createElement
  * @desc Creates an element
  * @param {string} tag The node tag e.g. div
  * @param {object} attributes The object's attributes
  * @returns {node} The created element
  */
const createElement = (tag, attributes) => {
  let element = document.createElement(tag);
  if (attributes !== null) {
    for (var name in attributes) {
      if (element[name] !== undefined) {
        element[name] = attributes[name];
      } else {
        element.setAttribute(name, attributes[name]);
      }
    }
  }

  return element;
}

/**
  * isScrolledIntoView
  * @desc Checks whether an element is scrolled into view
  * @param {node} elem The element to examine
  * @param {number} offset An offset modifier (if required)
  * @returns {boolean} that reflects the scroll view status of an element
  */
const isScrolledIntoView = (elem, offset = 0) => {
  const rect = elem.getBoundingClientRect();
  const elemTop = rect.top;
  const elemBottom = rect.bottom - offset;

  return (elemTop >= 0) && (elemBottom <= window.innerHeight);
}

/**
  * elementScrolledIntoView
  * @desc A promise that resolves when an element is scrolled into view
  * @param {node} elem The element to examine
  * @param {number} offset An offset modifier (if required)
  * @returns {promise} a promise that resolves once the element scrolls into the view
  */
const elementScrolledIntoView = (elem, offset = 0) => {
  return new Promise(resolve => {
    const handler = (e) => {
      if (isScrolledIntoView(elem, offset)) {
        document.removeEventListener('scroll', handler);
        resolve();
      }
    };

    document.addEventListener('scroll', handler);
  });
}

/**
  * getCookie
  * @desc Gets the CSRF token
  *       Ref @ https://docs.djangoproject.com/en/4.1/howto/csrf/
  * 
  * @param {string} name the name of the cookie
  * @returns {any} the cookie's value
  */
const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }

  return cookieValue;
};

/**
  * getCurrentHost
  * @desc Returns the current protocol and host
  * @returns {string} e.g. http://google.com
  */
const getCurrentHost = () => window.location.protocol + '//' + window.location.host;

/**
  * getCurrentPath
  * @desc Returns the path without the protocol and host
  *       e.g. http://google.com/some/location is now /some/location/
  * @returns {string} e.g. /some/location
  */
const getCurrentPath = () => {
  let path = window.location.pathname;
  path = path.replace(/\/$/, '');
  return decodeURIComponent(path);
}

/**
 * getCurrentURL
 * @desc Returns the current path without any parameters
 *       e.g. http://google.com/some/location?parameter=value is now http://google.com/some/location
 */
const getCurrentURL = () => `${getCurrentHost()}${location.pathname}`;

/**
 * getCurrentBrandPrefix
 * @desc Returns the current brand based on URL, e.g. '/HDRUK'
 * @returns {string}
 */
const getCurrentBrandPrefix = () => {
  const brand = document.documentElement.getAttribute('data-brand');
  if (isNullOrUndefined(brand) || isStringEmpty(brand) || brand === 'none') {
    return '';
  }

  return '/' + brand; 
}

/**
 * getBrandedHost
 * @desc Returns the branded host based on URL, e.g. '/HDRUK' if non-prod, otherwise
 *       returns its appropriate domain
 * @returns {string}
 */
const getBrandedHost = () => {
  const host = getCurrentHost();
  const brand = document.documentElement.getAttribute('data-brand');
  const isUnbranded = isNullOrUndefined(brand) || isStringEmpty(brand) || brand === 'none';
  if (host === 'https://phenotypes.healthdatagateway.org' || isUnbranded) {
    return host;
  }

  return `${host}/${brand}`;
}

/**
  * domReady
  * @desc A promise that resolves when the DOM is ready
  * @returns {promise}
  */
const domReady = new Promise(resolve => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', resolve);
  } else {
    resolve();
  }
});

/**
  * assert
  * @desc Throws an error message if a condition is not met
  * @param {boolean} condition a conditional value
  * @param {message} string a message to log if the condition resolves to a falsy value
  * 
  */
const assert = (condition, message) => {
  if (!condition) {
    throw message;
  }
}

/**
 * isNullOrUndefined
 * @desc returns true if the parameter is null or undefined
 * @param {any} value the value to consider
 * @returns {boolean} reflecting whether the value is null or undefined
 * 
 */
const isNullOrUndefined = (value) => typeof value === 'undefined' || value === null;

/**
 * isStringEmpty
 * @desc checks if a string is empty
 * @param {string|any} value the value to consider
 * @returns {boolean} determines whether the value is (a) undefined; or (b) empty
 * 
 */
const isStringEmpty = (value) => isNullOrUndefined(value) || !value.length;

/**
 * isStringWhitespace
 * @desc checks if a string is compose of only whitespace
 * @param {string} value the value to consider
 * @returns {boolean} reflecting whether the string contains only whitespace
 * 
 */
const isStringWhitespace = (value) => !value.replace(/\s/g, '').length;

/**
 * clearAllChildren
 * @desc removes all children from a node
 * @param {node} element the node to remove
 * @param {fn} cond conditional to determine fate of elem
 */
const clearAllChildren = (element, cond) => {
  for (const [index, child] of Object.entries(element.children)) {
    if (child.nodeType == 1 && cond && cond(child)) {
      continue;
    }
    element.removeChild(child);
  }
}

/**
 * redirectToTarget
 * @desc onClick handler for content cards, primarily used for ./search page - referral to detail page
 * @param {node} element the clicked node
 */
const redirectToTarget = (elem) => {
  const target = elem.getAttribute('data-target');
  if (!target) {
    return;
  }
  
  window.location.href = target;
}

/**
 * tryOpenFileDialogue
 * @desc attempts to open a file dialogue and returns the resulting file(s) through a callback
 * @param {object} options This method utilises ES6 destructing for setting default params
 *  -> @param {boolean} allowMultiple whether to allow multiple file uploads, if blank or false,
 *                                will only allow a single file to be uploaded
 *  -> @param {null, list} extensions the expected file extensions (leave null for all file types)
 *  -> @param {null, function(selected[bool], files[list])} callback the callback function for when a file is selected
 * 
 * e.g. usage:
 * 
 * ```js
 *  const files = tryOpenFileDialogue({ extensions: ['.csv', '.tsv'], callback: (selected, files) => {
 *    if (!selected) {
 *      return;
 *    }
 * 
 *    console.log(files); --> [file_1, ..., file_n]
 *  }});
 * ```
 * 
 */
const tryOpenFileDialogue = ({ allowMultiple = false, extensions = null, callback = null }) => {
  const input = document.createElement('input');
  input.type = 'file';

  if (allowMultiple) {
    input.multiple = true;
  }

  if (!isNullOrUndefined(extensions)) {
    input.accept = extensions.join(',');
  }

  input.addEventListener('change', (e) => {
    if (!isNullOrUndefined(callback)) {
      callback(e.target.files.length > 0, e.target.files);
    }
    input.remove();
  });

  input.click();
}

/**
 * interpolateString
 * @desc Interpolate string template
 *       Ref @ https://stackoverflow.com/posts/41015840/revisions
 * 
 * @param  {str} str The string to interpolate
 * @param  {object} params The parameters
 * @return {str} The interpolated string
 * 
 */
const interpolateString = (str, params) => {
  let names = Object.keys(params);
  let values = Object.values(params);
  return new Function(...names, `return \`${str}\`;`)(...values);
}

/**
 * parseHTMLFromString
 * @desc given a string of HTML, will return a parsed DOM
 * @param {str} str The string to parse as DOM elem
 * @returns {DOM} the parsed html
 */
const parseHTMLFromString = (str) => {
  const parser = new DOMParser();
  return parser.parseFromString(str, 'text/html');
}

/**
 * countUnique
 * @desc counts the unique elements in an array
 * @param {iterable} array counts the number of unique elements
 * @return {integer} number of unique elements
 */
const countUniqueElements = (iterable) => new Set(iterable).size;

/**
 * transformTitleCase
 * @desc transforms a string to TitleCase
 * @param {string} str the string to transform
 * @returns {string} the resultant, transformed string
 */
const transformTitleCase = (str) => {
  return str.replace(/\w\S*/g, (text) => text.charAt(0).toLocaleUpperCase() + text.substring(1).toLocaleLowerCase());
}

/**
 * tryGetRootElement
 * @desc Iterates through the parent of an element until it either
 *      (a) lapses by not finding an element that matches the class
 *      (b) finds the parent element that matches the class
 * @param {node} item the item to recursively examine
 * @param {string} expectedClass the expected class name 
 * @return {node|none} the parent element, if found
 */
const tryGetRootElement = (item, expectedClass) => {
  if (isNullOrUndefined(item)) {
    return null;
  }

  if (item.classList.contains(expectedClass)) {
    return item;
  }

  while (!isNullOrUndefined(item.parentNode) && item.parentNode.classList) {
    item = item.parentNode;
    if (item.classList.contains(expectedClass)) {
      return item;
    }
  }

  return null;
}

/**
 * tryGetRootNode
 * @desc Iterates through the parent of an element until it either
 *      (a) lapses by not finding an element that matches the node
 *      (b) finds the parent element that matches the node
 * @param {node} item the item to recursively examine
 * @param {string} expectedNode the expected node type 
 * @return {node|none} the parent element, if found
 */
const tryGetRootNode = (item, expectedNode) => {
  if (isNullOrUndefined(item)) {
    return null;
  }

  if (item.nodeName === expectedNode) {
    return item;
  }

  while (!isNullOrUndefined(item.parentNode) && item.parentNode.nodeName) {
    item = item.parentNode;
    if (item.nodeName === expectedNode) {
      return item;
    }
  }

  return null;
}

/**
 * getDeltaDiff
 * @desc gets the delta diff between two objects
 * @param {array} lhs the original object
 * @param {array} rhs the object to compare it with
 * @returns {array} an array where the rows reflect the diff between both objects
 * 
 */
const getDeltaDiff = (lhs, rhs) => {
  return [...new Set([...Object.keys(lhs), ...Object.keys(rhs)])].reduce((filtered, key) => {
    if (lhs?.[key] && rhs?.[key] && typeof lhs[key] === 'object' && typeof rhs[key] === 'object') {
      let diff = getDeltaDiff(lhs[key], rhs[key]);
      if (diff.length > 0) {
        filtered.push(...diff.map(([i, ...val]) => [`${key} ${i}`, ...val]));
      }
      
      return filtered;
    }

    if (key in rhs && !(key in lhs)) {
      filtered.push([key, 'created', rhs[key]]);
      return filtered;
    }
    
    if (key in lhs && !(key in rhs)) {
      filtered.push([key, 'deleted', lhs[key]]);
      return filtered;
    }

    if (lhs[key] === rhs[key]) {
      return filtered;
    }

    filtered.push([key, 'modified', lhs[key], rhs[key]]);
    return filtered;
  }, []);
}

/**
 * hasDeltaDiff
 * @desc tests whether two objects have been changed
 * @param {object} lhs the original object
 * @param {object} rhs the object to compare it with
 * @returns {boolean} reflects whether the object has been changed
 */
const hasDeltaDiff = (lhs, rhs) => {
  let diff = getDeltaDiff(lhs, rhs);
  return !!diff.length;
}

/**
 * parseDOI
 * @desc attempts to match a DOI in a string (.*\/gm)
 * @param {string} value the string to match
 * @returns {list} a list of matches
 */
const parseDOI = (value) => {
  return value.match(CLU_DOI_PATTERN);
}

/**
 * waitForElement
 * @desc waits for an element to exist based on selector parameter
 * @param {string} selector the string to match 
 * @returns {promise} promise that resolves with the given element
 */
const waitForElement = (selector) => {
  return new Promise(resolve => {
    if (document.querySelector(selector)) {
      return resolve(document.querySelector(selector));
    }

    const observer = new MutationObserver(() => {
      if (document.querySelector(selector)) {
        observer.disconnect();
        resolve(document.querySelector(selector));
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  });
}


/**
 * onElementRemoved
 * @desc waits for an element to be removed from the document before resolving
 * @param {node} element the element to observe
 * @returns {promise} promise that resolves when the given element is removed
 */
const onElementRemoved = (element) => {
  return new Promise(resolve => {
    const observer = new MutationObserver(() => {
      if (!document.body.contains(element)) {
        observer.disconnect();
        resolve();
      }
    });

    observer.observe(element.parentElement, { childList: true });
  });
}

/**
 * observeMatchingElements
 * @desc observes current and any future element(s) that matches the given selector
 * @param {string} selector the string to match 
 * @param {function} callback the callback method to handle the observed element 
 * @returns {null} no result
 */
const observeMatchingElements = (selector, callback) => {
  let elements = [];
  const observer = new MutationObserver(() => {
    if (document.querySelector(selector)) {
      elements = [...document.querySelectorAll(selector)].reduce((filtered, elem) => {
        if (filtered.indexOf(elem) >= 0) {
          return filtered;
        }

        callback(elem);
        filtered.push(elem);

        return filtered;
      }, elements);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}

/**
 * isArrayEqual
 * @desc det. whether an array is eq
 * @param {array} a an array
 * @param {array} b an array
 * @param {boolean} shouldSort whether to sort both arrays first
 * @returns {boolean} that refelects __eq state
 */
const isArrayEqual = (a, b, shouldSort = true) => {
  if (shouldSort) {
    a.sort();
    b.sort();
  }
  return a.length == b.length && a.every((ti, i) => { return ti == b[i]; });
}

/**
 * showLoader
 * @desc showing loader when fetching data
 */
const showLoader = () => {
  const loader = document.querySelector('.loading');
  loader.classList.add('display');
  setTimeout(() => {
    loader.classList.remove('display');
  }, 2000);
}

/**
 * hideLoader
 * @desc hide loader when fetching data
 */
const hideLoader = () => {
  const loader = document.querySelector('.loading');
  loader.classList.remove('display');
}

/**
 * startLoadingSpinner
 * @desc instantiate a loading spinner, either within an element or at the root <body/>
 * @param {node|null} container the container - if null, uses the <body/>
 * @returns {node} the spinner element or its container - whichever is topmost
 */
const startLoadingSpinner = (container) => {

  let spinner;
  if (isNullOrUndefined(container)) {
    container = document.body;

    spinner = createElement('div', {
      className: 'loading-spinner',
      innerHTML: '<div class="loading-spinner__icon"></div>'
    });
  } else {
    spinner = createElement('div', {
      className: 'loading-spinner__icon',
    });
  }
  container.appendChild(spinner)

  return spinner;
}

/**
 * convertMarkdownData
 * @desc converts HTML Markdown representation into a string
 * @param {node} parent the data node
 * @returns {string} a string representing the HTML Markdown Data
 */
const convertMarkdownData = (parent) => {
  let content = '';
  for (const child of parent.childNodes) {
    const tagName = child.tagName;
    if (tagName == 'BR' || (tagName == 'DIV' && !child.querySelector('br'))) {
      content += '\n';
    }

    if (child instanceof Text) {
      let textContent = child.textContent
      let isEmptyContent = isStringEmpty(textContent) || isStringWhitespace(textContent);
      if (child.previousSibling && !isEmptyContent) {
        textContent = '\n' + textContent;
      } else if (isEmptyContent) {
        textContent = '\n';
      }

      content += textContent;
      continue;
    }

    const prefix = child.previousSibling ? '\n' : '';
    content += prefix + convertMarkdownData(child);
  }

  return content;
}

/**
 * hasFixedElementSize
 * @desc det. whether an element's height/width is fixed
 * @param {node} element
 * @param {string[]} axes which axes to consider - if undefined/null is passed then both height and width will be examined
 * @returns {object} an object describing whether the element is has a fixed size for the given axis
 *                   _e.g._ `{ width: false, height: true }`
 * 
 */
const hasFixedElementSize = (element, axes = undefined) => {
  if (Array.isArray(axes)) {
    axes = axes.reduce((filtered, e) => {
      if (typeof(e) === 'string') {
        let value = e.toLowerCase();
        if (value === 'width' || value === 'height') {
          filtered.push(value);
        }
      }

      return filtered;
    }, []);
  }

  if (!Array.isArray(axes) || axes.length < 1) {
    axes = ['width', 'height'];
  }

  const results = { };
  for (let i = 0; i < axes.length; ++i) {
    let axis = axes[i];
    let size = element.style?.[axis];
    results[axis] = typeof(size) === 'string' ? (/\d/.test(size) && !/^(100|9\d)\%/.test(size)) : false;
  }

  return results;
}


/**
 * isElementSizeExplicit
 * @desc det. whether an element's height or width is explicit
 * @param {node} element the element to examine
 * @param {string[]} axes which axes to consider - if undefined/null is passed then both height and width will be examined
 * @returns {object} an object describing whether the element is explicitly sized alongside its current size
 *                   _e.g._ `{ width: { size: 10, explicit: false } }`
 * 
 */
const isElementSizeExplicit = (element, axes = undefined) => {
  const results = { };
  if (Array.isArray(axes)) {
    axes = axes.reduce((filtered, e) => {
      if (typeof(e) === 'string') {
        let value = e.toLowerCase();
        if (value === 'width' || value === 'height') {
          filtered.push(value);
        }
      }

      return filtered;
    }, []);
  }

  if (!Array.isArray(axes) || axes.length < 1) {
    axes = ['width', 'height'];
  }

  let container = document.querySelector('div#util-explicit-size');
  if (isNullOrUndefined(container)) {
    container = document.createElement('div');
    container.setAttribute('style', 'visibility: hidden !important; position: absolute !important;');
    container.appendTo(document.body);
  }

  let elementClone = element.clone();
  elementClone.appendTo(container);

  let elementRect = elementClone.getBoundingClientRect();
  for (let i = 0; i < axes.length; ++i) {
    let axis = axes[i];
    results[axis] = { size: elementRect?.[axis], explicit: true };
  }
  elementClone.innerHTML = '';

  elementRect = elementClone.getBoundingClientRect();
  for (const [ axis, packet ] of Object.entries(results)) {
    let size = packet?.size;
    let curr = elementRect?.[axis];
    if (curr < size) {
      results[axis].explicit = false;
    }
  }

  return results;
}
