/**
 * @desc resolves the plugin class associated with the specified name (if found)
 * 
 * @param {string}                      pluginName the name of the desired plugin
 * @param {Record<string, Object>|null} cache      optionally specify a cache if the manager hnd is to be instantiated just once; defaults to `null`
 * @param {Record<string, any>|null}    opts       optionally specify a recordset containing options to be supplied to the plugin constructor(s); defaults to `null`
 * 
 * @returns {Object|null} either (a) a `Record<str, Any>` describing the plugin's `handle` class and whether this cls was instantiated, or (b) null if plugin name is not known
 */
export const tryInitPluginManager = (pluginName, cache = null, opts = null) => {
  if (!stringHasChars(pluginName)) {
    return null;
  }

  const hasCache = isRecordType(cache);
  pluginName = pluginName.trim();

  if (hasCache && cache.hasOwnProperty(pluginName)) {
    const cached = cache[pluginName];
    if (isRecordType(cached)) {
      return { handle: cached.handle, wasInstantiated: false };
    }

    return null;
  }

  let hnd;
  switch (pluginName) {
    case 'tooltip':
      hnd = window.TooltipFactory;
      break;

    default:
      hnd = null;
      break;
  }

  if (!!hnd && hnd.toString().startsWith('class')) {
    opts = isRecordType(opts) && opts.hasOwnProperty(pluginName)
      ? opts[pluginName]
      : [];

    if (Array.isArray(opts)) {
      hnd = new hnd(...opts);
    } else if (typeof opts === 'function') {
      hnd = opts(pluginName, cache, opts);
    } else if (isRecordType(opts)) {
      if (Array.isArray(opts.instantiate)) {
        hnd = new hnd(...opts.instantiate);
      } else if (typeof opts.instantiate === 'function') {
        hnd = opts.instantiate(pluginName, cache, opts);
      }

      if (typeof opts.postInstantiate === 'function') {
        opts.postInstantiate(hnd, pluginName, cache, opts);
      }
    }

    if (typeof hnd === 'undefined' || hnd === null) {
      return null;
    }
  }

  if (hasCache) {
    cache[pluginName] = { handle: hnd, elements: [] };
  }

  return { handle: hnd, wasInstantiated: true };
};

/**
 * @desc requests an element be managed by a particular plugin
 * 
 * @param {string}                      pluginName  the name of the desired plugin
 * @param {HTMLElement}                 node        the HTMLElement to add to the specified plugin
 * @param {Array<Function>}             disposables optionally specify an array in which to store the dispose methods for use on cleanup
 * @param {Record<string, Object>|null} cache       optionally specify a cache if the manager hnd is to be instantiated just once; defaults to `null`
 * @param {Record<string, any>|null}    opts        optionally specify a recordset containing options to be supplied to the plugin constructor(s); defaults to `null`
 * 
 * @returns {Object|null} either (a) a `Record<str, Any>` describing the plugin's `handle` class and whether this cls was instantiated, or (b) null if plugin name is not known
 */
export const addElemToPlugin = (pluginName, node, disposables = null, cache = null, opts = null) => {
  const res = tryInitPluginManager(pluginName, cache, opts);
  if (!res) {
    return null;
  }

  res.handle.addElement(node);

  if (cache) {
    let cached = isRecordType(cache[pluginName]) && Array.isArray(cache[pluginName].elements)
      ? cache[pluginName]
      : null;

    if (!cached) {
      cached = { handle: hnd, elements: [] };
      cache[pluginName] = cached;
    }

    cached.elements.push(node);
  }

  if (res.handle.wasInstantiated && Array.isArray(disposables)) {
    if (res.handle.hasOwnProperty('dispose') && typeof res.handle.dispose === 'function') {
      disposables.push(() => res.handle.dispose());
    } else {
      opts = isRecordType(opts) && opts.hasOwnProperty(pluginName)
        ? opts[pluginName]
        : [];

      const disposer = isRecordType(opts) && typeof opts.dispose === 'function'
      if (disposer) {
        disposables.push(() => disposer(res.handle, pluginName, cache, opts));
      }
    }
  }

  return res;
}

/**
 * @desc initialises plugin managers for page components
 * 
 * @param {object}                     param0                    plugin behaviour opts
 * @param {HTMLElement}                param0.parent             optionally a HTMLElement in which to find popover menu item(s); defaults to `document`
 * @param {Record<string, Array<any>>} param0.options            optionally specify a set of options describing plugin constructor arguments for each plugin type
 * @param {boolean}                    param0.observeMutations   optionally specify whether to observe the addition & removal of plugin items; defaults to `false`
 * @param {boolean}                    param0.observeDescendants optionally specify whether to observe the descendant subtree when observing descendants; defaults to `false`
 */
export const managePlugins = ({
  parent = document,
  options = { },
  observeMutations = false,
  observeDescendants = false,
}) => {
  const elements = parent.querySelectorAll('[data-plugins]');

  const handlers = { };
  const disposables = [];
  for (let i = 0; i < elements.length; ++i) {
    const element = elements[i];

    let plugins = element.getAttribute('data-plugins');
    if (!stringHasChars(plugins)) {
      continue;
    }

    plugins = plugins.split(/(?:,|;)\s*/);
    for (let j = 0; j < plugins.length; ++j) {
      addElemToPlugin(plugins[j], element, disposables, handlers, options);
    }
  }

  if (observeMutations) {
    const observer = new MutationObserver((muts) => {
      for (let i = 0; i < muts.length; ++i) {
        const added = muts[i].addedNodes;
        for (let j = 0; j < added.length; ++j) {
          const node = added[j]
          if (!node.matches('[data-plugins]')) {
            continue;
          }

          let plugins = node.getAttribute('data-plugins');
          if (!stringHasChars(plugins)) {
            continue;
          }

          plugins = plugins.split(/(?:,|;)\s*/);
          for (let j = 0; j < plugins.length; ++j) {
            addElemToPlugin(plugins[j], element, disposables, handlers, options);
          }
        }
      }
    });

    observer.observe(parent, { subtree: observeDescendants, childList: true });
    disposables.push(() => observer.disconnect());
  }

  return disposables;
};
