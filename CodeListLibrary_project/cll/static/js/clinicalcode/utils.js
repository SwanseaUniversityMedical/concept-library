/* CONSTANTS */
const
  /**
   * CLU_DOMAINS
   * @desc Domain host targets
   */
  CLU_DOMAINS = {
    ROOT: 'https://conceptlibrary.saildatabank.com',
    HDRUK: 'https://phenotypes.healthdatagateway.org',
  }
  /**
   * CLU_TRANSITION_METHODS
   * @desc defines the transition methods associated
   *       with the animation of an element
   * 
   */
  CLU_TRANSITION_METHODS = {
    'transition': 'transitionend',
    'WebkitTransition': 'webkitTransitionEnd',
    'OTransition': 'oTransitionEnd otransitionend',
    'MozTransition': 'mozTransitionEnd',
  },
  /**
   * CLU_DOI_PATTERN
   * @desc Regex pattern to match DOI
   */
  CLU_DOI_PATTERN = /\b(10[.][0-9]{4,}(?:[.][0-9]+)*\/(?:(?!["&'<>])\S)+)\b/gm,
  /**
   * CLU_OBJ_PATTERN
   * @desc Regex pattern to match `[object (.*)]` classname
   * 
   */
  CLU_OBJ_PATTERN = /^\[object\s(.*)\]$/,
  /**
   * CLU_TRIAL_LINK_PATTERN
   * @desc Regex pattern to match urls
   *
   */
  CLU_TRIAL_LINK_PATTERN = /^(https?:\/\/)([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(:\d+)?(\/\S*)?$/gm,
  /**
   * CLU_URL_PATTERN
   * @desc Regex pattern matching URLs
   * @type {RegExp}
   */
  CLU_URL_PATTERN = new RegExp(
    /((https?|ftps?):\/\/[^"<\s]+)(?![^<>]*>|[^"]*?<\/a)/,
    'gm'
  ),
  /**
   * CLU_CSS_IMPORTANT
   * @desc important suffix for DOM styling
   * @type {string}
   */
  CLU_CSS_IMPORTANT = 'important!',
  /**
   * CLU_ORIGIN_TYPE
   * @desc URL origin descriptor enum
   * @readonly
   * @enum {string}
   */
  CLU_ORIGIN_TYPE = {
    Unknown   : 'Unknown',
    Malformed : 'Malformed',
    Empty     : 'Empty',
    Internal  : 'Internal',
    External  : 'External',
  };


/* UTILITIES */

/**
 * getObjectClassName
 * @desc derives the given object's classname
 * @param {any} val the value to examine
 * @returns {string} the classname describing the object
 */
const getObjectClassName = (val) => {
  if (val === null) {
    return 'null';
  } else if (typeof val === 'undefined') {
    return 'undefined';
  }

  try {
    if (val.constructor == Object && !(typeof val === 'function')) {
      return 'Object';
    }
  }
  finally {
    return Object.prototype.toString
      .call(val)
      .match(CLU_OBJ_PATTERN)[1];
  }
}

/**
 * isObjectType
 * @desc determines whether a value is an Object type
 * @param {any} val the value to check
 * @returns {boolean} a boolean describing whether the value is an Object 
 */
const isObjectType = (val) => {
  if (typeof val !== 'object' || val === null) {
    return false;
  }

  let className = getObjectClassName(val);
  return className === 'Object' || className === 'Map';
}

/**
 * isRecordType
 * @desc Record (Object) type guard
 * 
 * @param {*} obj some object to evaluate
 * 
 * @returns {boolean} flagging whether this object is Record-like
 */
const isRecordType = (obj) => {
  return typeof obj === 'object' && obj instanceof Object && obj.constructor === Object;
}

/**
 * isCloneableType
 * @desc determines whether a value is a structured-cloneable type
 *       as described by its specification, reference to the supported
 *       types can be found here: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Structured_clone_algorithm#supported_types
 * 
 * @param {any} val the value to check
 * @returns {boolean} a boolean describing whether the value is of a
 *                    structured-cloneable type
 */
const isCloneableType = (val) => {
  if (Object(val) !== val || val.constructor == Object) {
    return true;
  }

  let className = getObjectClassName(val);
  switch (className) {
    case 'Date':
    case 'Blob':
    case 'Number':
    case 'String':
    case 'RegExp':
    case 'Boolean':
    case 'FileList':
    case 'ImageData':
    case 'ArrayBuffer':
    case 'ImageBitmap':
      return true;

    case 'Set':
      return [...val].every(isCloneableType);

    case 'Map': {
      return [...val.entries()]
        .every(element => isCloneableType(element[0]) && isCloneableType(element[1]));
    }

    case 'Array':
    case 'Object': {
      return Object.keys(val)
        .every(key => isCloneableType(val[key]))
    }
  }

  return false;
}

/**
 * cloneObject
 * @desc Simplistic clone of an object/array
 * 
 * @param {object|array} obj the object to clone
 * 
 * @returns {array|object} the cloned object
 */
const cloneObject = (obj) => {
  const className = getObjectClassName(obj);
  switch (className) {
    case 'Set': {
      if ([...obj].every(isCloneableType)) {
        return structuredClone(obj);
      }

    } break;

    case 'Map': {
      const cloneable =- [...obj.entries()].every(x => isCloneableType(x[0]) && isCloneableType(x[1]));
      if (cloneable) {
        return structuredClone(obj);
      }

    } break;

    case 'Array': {
      const result = [];
      Object.keys(obj).forEach(key => {
        result[key] = cloneObject(obj[key]);
      });

      return result;
    }

    case 'Object': {
      const result = {};
      Object.keys(obj).forEach(key => {
        result[key] = cloneObject(obj[key]);
      });

      return result;
    }

    default:
      return obj;
  }
}

/**
  * deepCopy
  * @desc Performs a deep clone of the object i.e. recursive clone
  * @param {any} obj The object to clone
  * @returns {any} The cloned object
  */
const deepCopy = (obj) => {
  let className = getObjectClassName(obj);
  if (isCloneableType(obj) && window.structuredClone && typeof structuredClone === 'function') {
    let result;
    try {
      result = structuredClone(obj);
    }
    catch (err) {
      if (className === 'Object' || className === 'Array') {
        return cloneObject(obj);
      }

      throw err;
    }

    return result;
  }

  switch (className) {
    case 'Set':
    case 'Map':
    case 'Array':
    case 'Object':
      return JSON.parse(JSON.stringify(obj));

    default:
      break
  }

  return obj;
}

/**
  * mergeObjects
  * @desc Merges two objects together where the first object takes precedence (i.e., it's not overriden)
  * @param {object} a An object to clone that takes precedence
  * @param {object} b The object to clone and merge into the first object
  * @param {boolean} copy Whether to copy the object(s)
  * @returns {object} The merged object
  */
const mergeObjects = (a, b, copy = false) => {
  if (copy) {
    a = deepCopy(a);
  }

  Object.keys(b)
    .forEach(key => {
      if (key in a) {
        return;
      }

      let value = b[key];
      if (copy) {
        a[key] = deepCopy(value);
      } else {
        a[key] = value;
      }
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
 * @desc attempts to parse the global listener key
 * 
 * @param {string} key the desired global listener key name
 * 
 * @returns {object|null} specifying the namespace, name, and type of listener; will return `null` if invalid
 */
const parseListenerKey = (key) => {
  if (typeof key !== 'string' || !stringHasChars(key)) {
    return null;
  }

  let target = key.trim().split(':');
  if (target.length === 2) {
    key = target[1];
    target = target[0].split('.');
    return {
      name: target?.[1] ?? key,
      type: key,
      namespace: target[0],
    };
  }

  return {
    name: target[0],
    type: target[0],
    namespace: '__base',
  };
}

/**
 * @param {string|null} namespace optionally specify the global namespace listener key
 * 
 * @returns {object} specifying the global listener event(s)
 */
const getGlobalListeners = (namespace = null) => {
  let listeners = window.hasOwnProperty('__globalListeners') ? window.__globalListeners : null;
  if (!isRecordType(listeners)) {
    listeners = { };
    window.__globalListeners = listeners;
  }

  if (typeof namespace === 'string' && stringHasChars(namespace)) {
    let group = listeners?.[namespace];
    if (!group) {
      group = { };
      listeners[namespace] = group;
    }

    return group;
  }

  return listeners;
}

/** 
 * @param {string|object} key either (a) the event key; or (b) a parsed event key per `parseListenerKey()`
 * 
 * @returns {boolean} specifying whether a listener exists at the given key
 */
const hasGlobalListener = (key) => {
  let listeners = window.hasOwnProperty('__globalListeners') ? window.__globalListeners : null;
  if (!isRecordType(listeners)) {
    return false;
  }

  if (!isRecordType(key)) {
    key = parseListenerKey(key);
  }

  if (!key) {
    return false;
  }

  return !!(listeners?.[key.namespace]?.[key.name]);
}

/**
 * @desc utility method to listen to an event relating to a set of elements matched by the given CSS selector
 * 
 * @param {string|object}    key      either (a) the event key; or (b) a parsed event key per `parseListenerKey()`
 * @param {string}           selector a CSS selector to compare against the event target
 * @param {Function}         callback a callback function to call against each related event target
 * @param {object}           opts     optionally specify the event listener options; defaults to `undefined`
 * @param {HTMLElement|null} parent   optionally specify the parent element context; defaults to `document` otherwise
 * 
 * @returns {Function} a disposable to cleanup this listener
 */
const createGlobalListener = (key, selector, callback, opts = undefined, parent = document) => {
  if (!stringHasChars(selector) || !isHtmlObject(parent)) {
    return null;
  }

  if (!isRecordType(key)) {
    key = parseListenerKey(key);
  }

  if (!key) {
    return null;
  }

  let hnd;
  const listeners = getGlobalListeners(key.namespace);

  const handler = (e) => {
    const target = e.target;
    if (!target || !target.matches(selector)) {
      return;
    }

    callback(e);
  };

  const dispose = () => {
    const prev = listeners?.[key.name];
    if (!!hnd && prev === hnd) {
      delete listeners[key.name];
    }

    parent.removeEventListener(key.type, handler, opts);
  };

  hnd = { ...key, dispose };
  listeners[key.name] = hnd;

  parent.addEventListener(key.type, handler, opts);
  return dispose;
}

/**
 * @param {string|object} key either (a) the event key; or (b) a parsed event key per `parseListenerKey()`
 * 
 * @returns {boolean} specifying whether a listener was disposed at the given key 
 */
const removeGlobalListener = (key) => {
  if (!isRecordType(key)) {
    key = parseListenerKey(key);
  }

  if (!key) {
    return false;
  }

  const listeners = getGlobalListeners(key.namespace);
  const listenerHnd = listeners?.[key.name];
  if (!listenerHnd) {
    return false;
  }

  listenerHnd.dispose();
  return true;
}

/**
  * createElement
  * @desc Creates a DOM element
  * 
  * @note
  * If the `behaviour` property is specified as sanitisation behaviour you should note that it expects _three_ key-value pairs, such that:
  *   1. `key`   - sanitisation behaviour opts for the key component
  *   2. `value` - sanitisation behaviour opts for the attribute value component
  *   3. `html`  - specifies how to sanitise HTML string children
  * 
  * @param {string}                 tag The node tag e.g. div
  * @param {object}          attributes The object's attributes
  * @param {object|boolean}   behaviour Optionally specify the sanitisation behaviour of attributes; supplying a `true` boolean will enable strict sanitisation
  * @param {...*}              children Optionally specify the children to be appended to this element
  * 
  * @returns {node} The created element
  */
const createElement = (tag, attributes = null, behaviour = null, ...children) => {
  if (!!behaviour && typeof behaviour === 'boolean') {
    behaviour = { key: { }, value: { }, html: { USE_PROFILES: { html: true, mathMl: false, svg: true, svgFilters: false } } };
  }

  let udfSanHtml, ustrSanitise;
  if (!isRecordType(behaviour)) {
    behaviour = null;
    udfSanHtml = { USE_PROFILES: { html: true, mathMl: false, svg: true, svgFilters: false } };
    ustrSanitise = (_type, value) => value;
  } else {
    udfSanHtml = isRecordType(behaviour.udfSanHtml) ? behaviour.udfSanHtml : null;
    ustrSanitise = (type, value) => {
      const opts = behaviour?.[type];
      if (opts) {
        return strictSanitiseString(value, opts);
      }

      return value;
    };
  }

  let element = document.createElement(tag);
  if (isRecordType(attributes)) {
    let attr;
    for (let name in attributes) {
      name = ustrSanitise('key', name);
      attr = attributes[name];
      switch (name) {
        case 'class': {
          element.classList.add(ustrSanitise('value', attr));
        } break;

        case 'className': {
          element.className = ustrSanitise('value', attr);
        } break;

        case 'classList': {
          if (Array.isArray(attr)) {
            for (let i = 0; i < attr.length; ++i) {
              element.classList.add(ustrSanitise('value', attr[i]));
            }
          } else {
            element.classList.add(ustrSanitise('value', attr));
          }
        } break;

        case 'dataset': {
          for (let key in attr) {
            element.dataset[key] = ustrSanitise('value', attr[key]);
          }
        } break;

        case 'attributes': {
          for (let key in attr) {
            element.setAttribute(key, ustrSanitise('value', attr[key]));
          }
        } break;

        case 'text':
        case 'innerText': {
          element.textContent = attr;
        } break;

        case 'html':
        case 'innerHTML': {
          let res;
          if (typeof attr === 'string') {
            res = parseHTMLFromString(attr.trim(), !udfSanHtml, udfSanHtml);
          } else if (isRecordType(attr)) {
            const src = attr.src;
            if (typeof src !== 'string') {
              break;
            }

            const ignore = !!attr.noSanitise;
            const params = Array.isArray(attr.sanitiseArgs) ? attr.sanitiseArgs : [];
            res = parseHTMLFromString.apply(null, [src.trim(), ignore, ...params]);
          }

          if (Array.isArray(res)) {
            for (let i = 0; i < res.length; ++i) {
              if (!isHtmlObject(res[i])) {
                continue;
              }

              element.appendChild(res[i]);
            }
          }
        } break;

        case 'style': {
          let value, priority;
          if (isRecordType(attr)) {
            for (let key in attr) {
              value = ustrSanitise('value', attr[key]);
              priority = value.indexOf(CLU_CSS_IMPORTANT);
              if (priority > 0) {
                value = value.substring(priority, priority + CLU_CSS_IMPORTANT.length - 1);
                priority = 'important';
              } else {
                priority = value?.[3];
              }
              element.style.setProperty(key, value, priority);
            }
          } else if (Array.isArray(attr) && attr.length >= 2) {
            value = ustrSanitise('value', attr[0]);
            priority = value.indexOf(CLU_CSS_IMPORTANT);
            if (priority > 0) {
              attr = value.substring(priority, priority + CLU_CSS_IMPORTANT.length - 1);
              priority = 'important';
            } else {
              priority = attr?.[3];
            }

            element.style.setProperty(value, attr[1], priority);
          } else if (typeof attr === 'string') {
            element.style.cssText = ustrSanitise('value', attr);
          }
        } break;

        case 'childNodes': {
          if (Array.isArray(attr)) {
            for (let i = 0; i < attr.length; ++i) {
              element.appendChild(attr[i])
            }
          } else {
            element.appendChild(attr);
          }
        } break;

        case 'parent': {
          attr.appendChild(element);
        } break;

        default: {
          if (name.startsWith('on') && typeof attr === 'function') {
            element.addEventListener(name.substring(2), attr);
          } else if (!element.hasOwnProperty(name) || name.startsWith('data-')) {
            element.setAttribute(name, ustrSanitise('value', attr));
          } else {
            element[name] = ustrSanitise('value', attr);
          }
        } break;
      }
    }
  }

  let child;
  for (let i = 0; i < children.length; ++i) {
    child = children[i];
    if (typeof child === 'string' || typeof child === 'number') {
      child = document.createTextNode(child);
    }

    if (isHtmlObject(child)) {
      element.appendChild(child);
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
}

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
  if ((host === CLU_DOMAINS.HDRUK) || isUnbranded) {
    return host;
  }

  return `${host}/${brand}`;
}

/**
 * getBrandTargetURL
 * @desc Returns the brand URL target for management redirect buttons (used in navigation menu)
 * @param {string[]} brandTargets an array of strings containing the brand target names
 * @param {boolean} productionTarget a boolean flag specifying whether this is a production target
 * @param {Node} element the html event node
 * @param {string} oldRoot the path root (excluding brand context)
 * @param {string} path the window's location href
 * @returns {string} the target URL
 */
const getBrandTargetURL = (brandTargets, productionTarget, element, oldRoot, path) =>{
  const pathIndex = brandTargets.indexOf(oldRoot.toUpperCase()) == -1 ? 0 : 1;
  const pathTarget = path.split('/').slice(pathIndex).join('/');

  let elementTarget = element.getAttribute('value');
  if (!isStringEmpty(elementTarget)) {
    elementTarget = `${elementTarget}/${pathTarget}`;
  } else {
    elementTarget = pathTarget;
  }

  let targetLocation;
  if (!productionTarget) {
    targetLocation = `${document.location.origin}/${elementTarget}`;
  } else {
    switch (elementTarget) {
      case '/HDRUK': {
        targetLocation = `${CLU_DOMAINS.HDRUK}/${pathTarget}`;
      } break;

      default: {
        const isHDRUKSubdomain = window.location.href
          .toLowerCase()
          .includes('phenotypes.healthdatagateway');

        targetLocation = isHDRUKSubdomain ? CLU_DOMAINS.ROOT : document.location.origin;
        targetLocation = `${targetLocation}/${elementTarget}`;
      } break;
    }
  }

  window.location.href = strictSanitiseString(targetLocation);
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
const isStringEmpty = (value) => typeof value !== 'string' || !value.length;

/**
 * isStringWhitespace
 * @desc checks if a string is compose of only whitespace
 * @param {string} value the value to consider
 * @returns {boolean} reflecting whether the string contains only whitespace
 * 
 */
const isStringWhitespace = (value) => typeof value !== 'string' || !value.replace(/\s/g, '').length;

/**
 * stringHasChars
 * @desc checks if a `string` has any number of characters aside from whitespace chars
 * @param {string} value the value to consider
 * @returns {boolean} specifying whether the `string` has chars
 */
const stringHasChars = (value) => typeof value === 'string' && value.length && value.replace(/\s/g, '').length;

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

  window.location.href = strictSanitiseString(target);
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
  ```js
    const files = tryOpenFileDialogue({ extensions: ['.csv', '.tsv'], callback: (selected, files) => {
      if (!selected) {
        return;
      }

      console.log(files); --> [file_1, ..., file_n]
    }});
  ```
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
 * @param {RegExp} pattern the pattern to be matched
 * @returns {RegExpMatchArray} a list of matches
 */
const parseString = (value, pattern) => {
  return value.match(pattern);
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
 * 
 * @param {node|null} container   optionally specify the container - if null, uses the <body/>
 * @param {boolean}   fillContent optionally specify whether to apply the absolute fill style; defaults to `false`
 * 
 * @returns {node} the spinner element or its container - whichever is topmost
 */
const startLoadingSpinner = (container, fillContent = false) => {
  let spinner;
  if (isNullOrUndefined(container)) {
    container = document.body;

    spinner = createElement('div', {
      className: 'loading-spinner',
      childNodes: [
        createElement('div', { className: 'loading-spinner__icon' })
      ],
    });
  } else if (fillContent) {
    spinner = createElement('div', {
      className: 'loading-spinner loading-spinner--absolute',
      childNodes: [
        createElement('div', { className: 'loading-spinner__icon' })
      ],
    });
  } else {
    spinner = createElement('div', { className: 'loading-spinner__icon' });
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
    if (child instanceof Text) {
      let textContent = child.textContent
      let isEmptyContent = isStringEmpty(textContent) || isStringWhitespace(textContent);
      if (isEmptyContent) {
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

  let elementClone = element.cloneNode(true);
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

/**
 * linkifyText
 * @desc process a plain-text string, finding all valid URLs and converts them to HTML tags as specified by the given options
 * 
 * @example
 * const source = `Some block of text describing URLs:
 *     1. http://some-website.co.uk
 *     2. https://some-url.co.uk/
 *     3. The inner link here processed: <p>http://website.com</p>
 *     4. This anchor is ignored: <a href="http://ignored-link.com">http://ignored.com</a>
 *     5. This link is ignored: <div data-link="https://ignored.com"></div>
 *     6. http://some-removed-link.com
 *     7. http://some-replaced-link.com
 *     8. http://retarget-underlying-text.com
 * `;
 * 
 * const result = linkifyText(
 *   // The text to process
 *   source,
 *   // Optionally specify a set of options
 *   {
 *     // Optionally specify default anchor attributes 
 *     cls: 'some-anchor-class',
 *     rel: 'noopener',
 *     trg: '_blank',
 *     // Optionally specify a callback to process the url
 *     //   -> [Fallthrough]: return `null | undefined` to accept defaults
 *     //   -> [   Retarget]: return `{ retarget: string }` to retarget the underlying text
 *     //   -> [   Deletion]: return `{ remove: true }` to remove the link entirely
 *     //   -> [    Replace]: return `{ replace: string }` to skip linkify and replace with text
 *     //   -> [VaryContent]: return `{ url?: string, title?: string, rel?: string, trg?: string, cls?: string }`
 *     anchorCallback: (url, offset, text) => {
 *       const idx = text.lastIndexOf('.', offset);
 *       const pos = text.substring(idx - 1, idx);
 *       if (pos === '6') {
 *         return { remove: true };
 *       } else if (pos === '7') {
 *         return { replace: '{REDACTED}' };
 *       } else if (pos === '8') {
 *         return { retarget: text.substring(0, idx - 1) + text.substring(offset + url.length) };
 *       }
 * 
 *       return { title: 'Linkified', rel: 'noopener noreferrer' };
 *     },
 *     // Optionally specify a callback to render the URL
 *     //   -> The arguments given to the callback are derived from the default set and may be varied by the `anchorCallback`
 *     //   -> Returning an empty or non-string-like object will 
 *     renderCallback: (url, title, rel, trg, cls) => {
 *       return `<a href="${url}" rel="${rel}" target="${trg}" class="${cls}">${title}</a>`;
 *     },
 *   }
 * );
 * 
 * @param {string}   source                            the string to process
 * @param {Object}   [param1]                          optionally specify a set of options that vary this function's behaviour 
 * @param {string}   [param1.cls]                      optionally specify the anchor's `class` attribute
 * @param {string}   [param1.rel='noopener']           optionally specify the relationship between the linked resource and this document; defaults to `noopener`
 * @param {string}   [param1.trg='_blank']             optionally specify how to display the linked resource; defaults to `_blank`
 * @param {Function} [param1.anchorCallback=undefined] optionally specify a callback to vary processed links; defaults to `undefined`
 * @param {Function} [param1.renderCallback=undefined] optionally specify a callback to render processed links; defaults to `undefined`
 * 
 * @returns {string} the processed text
 */
const linkifyText = (
  source,
  { cls = '', rel = 'noopener', trg = '_blank', anchorCallback = undefined, renderCallback = undefined } = {}
) => {
  if (isNullOrUndefined(source) || isStringEmpty(source) || isStringWhitespace(source)) {
    return '';
  }

  if (typeof cls !== 'string') {
    cls = '';
  }

  if (typeof rel !== 'string') {
    rel = '';
  }

  if (typeof trg !== 'string') {
    trg = '';
  }

  const hasAnchorCallback = typeof anchorCallback === 'function',
        hasRenderCallback = typeof renderCallback === 'function';

  let url, len, uTitle, uRel, uTarget, uClass;
  while ((match = CLU_URL_PATTERN.exec(source)) != null) {
    url = match[0], offset = match.index, len = url.length;
    uTitle = url, uRel = rel, uTarget = trg, uClass = cls;
    if (hasAnchorCallback) {
      const result = anchorCallback(url, offset, match.input);
      if (typeof result === 'object') {
        if (result?.replace) {
          const str = typeof result.replace === 'string' ? result.replace : String(result.replace);
          source = source.substring(0, offset) + str + source.substring(offset + len);
          continue;
        } else if (result?.retarget) {
          source = result.retarget;
          continue;
        }

        const shouldDelete = result?.remove;
        if (!shouldDelete) {
          if (typeof result?.url === 'string') {
            if (!isStringEmpty(result.url)) {
              url = result.url;
            } else {
              shouldDelete = true;
            }
          }

          if (typeof result?.title === 'string') {
            if (!isStringEmpty(result.title)) {
              uTitle = result.title;
            } else {
              shouldDelete = true;
            }
          }
        }

        if (shouldDelete) {
          source = source.substring(0, offset) + source.substring(offset + len);
          continue;
        }

        uRel = typeof result?.rel === 'string' ? result.rel : uRel;
        uClass = typeof result?.cls === 'string' ? result.cls : uClass;
        uTarget = typeof result?.trg === 'string' ? result.trg : uTarget;
      }
    }

    let result;
    if (hasRenderCallback) {
      result = renderCallback(url, uTitle, uRel, uTarget, uClass);
      if (typeof result !== 'string' || isStringEmpty(result)) {
        result = '';
      }
    } else {
      result = `<a href="${url}" rel="${uRel}" target="${uTarget}" class=${uClass}>${uTitle}</a>`;
    }

    source = source.substring(0, offset) + result + source.substring(offset + len);
  }

  return source;
}

/**
 * @desc determines whether the specified URL is malformed or not
 * 
 * @param {string|any} url some URL to evaluate
 * 
 * @returns {boolean} specifying whether this URL is valid
 */
const isValidURL = (url) => {
  if (!stringHasChars(url)) {
    return false;
  }

  try {
    url = new URL(url);
  } catch {
    return false;
  }

  return true;
}

/**
 * @desc determines the origin of the URL, i.e. whether it's external or internal
 * @note this function may resolve a `CLU_ORIGIN_TYPE.Empty` or `CLU_ORIGIN_TYPE.Malformed` value if the URL is empty/malformed
 * 
 * @param {string|any} url some URL to evaluate
 * 
 * @returns {enum<string>} a `CLU_ORIGIN_TYPE` descriptor
 */
const getOriginTypeURL = (url, forceBrand = true) => {
  if (!stringHasChars(url)) {
    return CLU_ORIGIN_TYPE.Empty;
  }

  let target, malformed;
  try {
    target = new URL(url);
    return target.origin !== window.location.origin ? CLU_ORIGIN_TYPE.External : CLU_ORIGIN_TYPE.Internal;
  } catch {
    malformed = true;
  }

  if (malformed) {
    try {
      if (forceBrand) {
        target = new URL(url, getBrandedHost());
      } else {
        target = new URL(url, getCurrentURL())
      }

      return target.origin !== window.location.origin ? CLU_ORIGIN_TYPE.External : CLU_ORIGIN_TYPE.Internal;
    }
    catch {
      return CLU_ORIGIN_TYPE.Malformed;
    }
  }

  return CLU_ORIGIN_TYPE.Internal;
}

/**
 * @desc determines whether the given URL is absolute/relative
 * @note where:
 *  - relative → _e.g._ `/some/path/` or `some/path`;
 *  - absolute → _e.g._ `https://some.website/some/path` _etc_.
 * 
 * @param {string} url some URL to evaluate
 * 
 * @returns {boolean} specifying whether the given URL is absolute
 */
const isAbsoluteURL = (url) => {
  return /^(?:[a-z]+:)?\/\//i.test(url);
}

/**
 * @desc opens the specified link on the client
 * @note attempts to replicate client content navigation via `<a/>` tags
 * 
 * @param {HTMLElement|string} link                either (a) some node specifying a `[href] | [data-link]` or (b) a `string` URL
 * @param {object}             param1              navigation optuions
 * @param {string|null}        param1.rel          optionally specify the `[rel]` attribute assoc. with this link; defaults to `null`
 * @param {string|null}        param1.target       optionally specify the `[target]` attribute assoc. with this link; defaults to `null`
 * @param {boolean}            param1.forceBrand   optionally specify whether to ensure that the Brand target is applied to the final URL; defaults to `true`
 * @param {boolean}            param1.followEmpty  optionally specify whether empty links (i.e. towards index page) can be followed; defaults to `true`
 * @param {boolean}            param1.allowNewTab  optionally specify whether `target=__blank` behaviour is allowed; defaults to `true`
 * @param {boolean}            param1.metaKeyDown  optionally specify whether to navigate as if the meta key is held (_i.e._ ctrl + click); defaults to `false`
 * @param {Event|null}         param1.relatedEvent optionally specify some DOM `Event` relating to this method (used to derive `ctrlKey` | `metaKey`); defaults to `null`
 * 
 * @returns 
 */
const tryNavigateLink = (link, {
  rel = null,
  target = null,
  forceBrand = true,
  followEmpty = true,
  allowNewTab = true,
  metaKeyDown = false,
  relatedEvent = null,
} = {}) => {
  let url;
  if (isHtmlObject(link)) {
    url = link.getAttribute('href');
    if (typeof url === 'string') {
      rel = rel ?? link.getAttribute('rel');
      target = target ?? link.getAttribute('target');
    } else {
      url = link.getAttribute('data-link');
      if (url) {
        rel = rel ?? link.getAttribute('data-linkrel');
        target = target ?? link.getAttribute('data-linktarget');
      }
    }
  } else if (typeof link === 'string') {
    url = link;
  }

  if (typeof url !== 'string') {
    return false;
  }

  const originType = getOriginTypeURL(url, forceBrand);
  if (originType === 'Malformed' || (originType === 'Empty' && !followEmpty)) {
    return false;
  }

  if (forceBrand && (originType === 'Internal' || originType === 'Empty')) {
    let brandedHost = getBrandedHost();
    brandedHost = new URL(brandedHost);

    const absolute = isAbsoluteURL(url);
    if (!absolute) {
      const hasSlash = url.startsWith('/');
      url = new URL(url, brandedHost.origin);

      if (hasSlash || originType === 'Empty') {
        const prefix = getCurrentBrandPrefix();
        if (!url.pathname.startsWith(prefix)) {
          url = new URL(prefix + url.pathname + url.search + url.hash, brandedHost.origin);
        }
      } else {
        let path = getCurrentURL();
        if (!path.endsWith('/')) {
          path += '/';
        }

        url = new URL(path + url.pathname.substring(1) + url.search + url.hash);
      }
    } else {
      url = new URL(url, brandedHost.origin);
      if (url.origin === CLU_DOMAINS.HDRUK && url.origin !== brandedHost.origin) {
        url = new URL(url.pathname + url.search + url.hash, brandedHost.origin);
      }
    }
  } else if (originType === 'Internal' || originType === 'Empty') {
    const absolute = isAbsoluteURL(url);
    if (!absolute) {
      if (!url.startsWith('/')) {
        let path = getCurrentURL();
        if (!path.endsWith('/')) {
          path += '/';
        }
  
        url = new URL(url, getCurrentHost());
        url = new URL(path + url.pathname.substring(1) + url.search + url.hash);
      } else {
        url = new URL(url, getCurrentHost());
      }
    } else {
      url = new URL(url);
    }
  } else {
    url = new URL(url);
  }

  const metaActive = metaKeyDown || (!!relatedEvent && (relatedEvent.ctrlKey || relatedEvent.metaKey));
  if (allowNewTab && (target === '__blank' || metaActive)) {
    window.open(url.href, '_blank', rel);
    return true;
  }

  window.location = url.href;
  return true;
}

/**
 * @desc a type-guard for `HTMLElement` | `HTMLNode` objects
 * 
 * @param {*}      obj         some DOM element to consider
 * @param {string} desiredType optionally specify the type, expects one of `element` | `node` | `any`; defaults to `Any`
 * 
 * @returns {boolean} specifies whether the given obj is a `HTMLElement` | `HTMLNode` as specified by the `desiredType` param
 */
const isHtmlObject = (obj, desiredType = 'Any') => {
  if (isNullOrUndefined(obj)) {
    return false;
  }

  if (typeof desiredType !== 'string') {
    desiredType = 'Any';
  }

  desiredType = desiredType.toLowerCase();
  if (desiredType.startsWith('html')) {
    desiredType = desiredType.substring(4);
  }

  let condition;
  switch (desiredType) {
    case 'node': {
      condition = typeof Node === 'object'
        ? obj instanceof Node
        : typeof obj === 'object' && typeof obj.nodeType === 'number' && typeof obj.nodeName === 'string';
    } break;

    case 'element': {
      condition = typeof HTMLElement === 'object'
        ? obj instanceof HTMLElement
        : typeof obj === 'object' && obj.nodeType === 1 && typeof obj.nodeName === 'string';
    } break;

    case 'any':
    default: {
      condition = (typeof Node === 'object' && typeof HTMLElement === 'object')
        ? (obj instanceof Node || obj instanceof HTMLElement)
        : typeof obj === 'object' && typeof obj.nodeType === 'number' && typeof obj.nodeName === 'string';
    } break;
  }

  return !!condition;
}

/**
 * @desc determines element visibility
 * @note does not check client window intersection
 * 
 * @param {HTMLElement} elem some DOM element to evaluate
 * 
 * @returns {boolean} specifies whether the elem is currently rendered
 */
const isVisibleObj = (elem) => {
  if (!isHtmlObject(elem, 'element')) {
    return false;
  }

  try {
    if (window.checkVisibility) {
      return elem.checkVisibility({
        opacityProperty: true,
        visibilityProperty: true,
        contentVisibilityAuto: true,
      });
    }

    const style = document.defaultView.getComputedStyle(elem);
    return (
      style.width !== '0' &&
      style.height !== '0' &&
      style.display != 'none' &&
      style.visibility !== 'hidden' &&
      Number(style.opacity) > 0
    );
  }
  catch {
    // Default true on failure
    return true;
  }
}