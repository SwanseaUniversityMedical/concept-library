const TRANSITION_METHODS = {
  'transition': 'transitionend',
  'WebkitTransition': 'webkitTransitionEnd',
  'OTransition': 'oTransitionEnd otransitionend',
  'MozTransition': 'mozTransitionEnd',
};

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

const mergeObjects = (a, b) => {
  Object.keys(b).forEach(key => {
    if (!(key in a))
      a[key] = b[key];
  });

  return a;
}

const matchesSelector = selector => callback => e => e.target.matches(selector) && callback(e);

const getTransitionMethod = () => {
  const root = document.documentElement;
  for (let method in TRANSITION_METHODS) {
    if (typeof root.style[method] !== 'undefined') {
      return TRANSITION_METHODS[method];
    }
  }

  return undefined;
}

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

const isScrolledIntoView = (elem, offset = 0) => {
  const rect = elem.getBoundingClientRect();
  const elemTop = rect.top;
  const elemBottom = rect.bottom - offset;

  if (offset > 0) {
    console.log(elemTop, elemBottom, window.innerHeight);
  }

  return (elemTop >= 0) && (elemBottom <= window.innerHeight);
}

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

const getCurrentHost = () => window.location.protocol + '//' + window.location.host;

const getCurrentPath = () => {
  let path = window.location.pathname;
  path = path.replace(/\/$/, '');
  return decodeURIComponent(path);
}

const domReady = new Promise(resolve => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', resolve);
  } else {
    resolve();
  }
});
