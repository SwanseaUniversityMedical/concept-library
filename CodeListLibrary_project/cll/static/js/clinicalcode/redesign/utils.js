const TRANSITION_METHODS = {
  'transition': 'transitionend',
  'WebkitTransition': 'webkitTransitionEnd',
  'OTransition': 'oTransitionEnd otransitionend',
  'MozTransition': 'mozTransitionEnd',
};

/**
  * deepCopy
  * @desc Performs a deep clone of the object i.e. recursive clone
  * @param {object} obj The object to clone
  * @returns {object} The cloned object
  */
const deepCopy = (obj) => {
  let clone = { };
  for (var i in obj) {
    if (obj[i] != null && typeof obj[i] == 'object') {
      clone[i] = deepCopy(obj[i]);
      continue;
    }

    clone[i] = obj[i];
  }

  return clone;
}

/**
  * mergeObjects
  * @desc Merges two objects together where the first object takes precedence (i.e., it's not overriden)
  * @param {object} a An object to clone that takes precedence
  * @param {object} b The object to clone
  * @returns {object} The cloned object
  */
const mergeObjects = (a, b) => {
  Object.keys(b).forEach(key => {
    if (!(key in a))
      a[key] = b[key];
  });

  return a;
}

/**
  * matchesSelector
  * @desc Tests whether an element's target matches a selector and calls a callback
  */
const matchesSelector = selector => callback => e => e.target.matches(selector) && callback(e);

/**
  * getTransitionMethod
  * @desc Finds the relevant transition method of the explorer
  * @returns {object} The transition method
  */
const getTransitionMethod = () => {
  const root = document.documentElement;
  for (let method in TRANSITION_METHODS) {
    if (typeof root.style[method] !== 'undefined') {
      return TRANSITION_METHODS[method];
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
  if (attributes != null) {
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
  * @returns {boolean}
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
  * @returns {promise}
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
  * @reference https://docs.djangoproject.com/en/4.1/howto/csrf/
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
  * @desc Returns the path without the protocol and host e.g. http://google.com/some/location is now /some/location/
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
 */
const getCurrentURL = () => `${getCurrentHost()}${location.pathname}`;

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
  */
const assert = (condition, message) => {
  if (!condition) {
    throw message;
  }
}

/**
 * isNullOrUndefined
 * @desc returns true if the parameter is null or undefined
 */
const isNullOrUndefined = (value) => typeof value === 'undefined' || value === null;

/**
 * isStringEmpty
 * @desc checks if a string is empty
 */
const isStringEmpty = (value) => isNullOrUndefined(value) || !value.length;

/**
 * isStringWhitespace
 * @desc checks if a string is compose of only whitespace
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
 * displayCardDetails
 * @desc onClick handler for content cards, primarily used for ./search page - referral to detail page
 * @param {node} element the clicked node
 */
const displayCardDetails = (elem) => {
  const target = elem.getAttribute('data-target');
  if (!target) {
    return;
  }
  
  window.location.href = target;
}
