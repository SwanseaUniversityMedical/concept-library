/**
 * @desc resolves the plugin class associated with the specified name (if found)
 * 
 * @param {string}                      pluginName the name of the desired plugin
 * @param {Record<string, Object>|null} cache      optionally specify a cache if the manager hnd is to be instantiated just once; defaults to `null`
 * @param {Record<string, any>|null}    options    optionally specify a recordset containing options to be supplied to the plugin constructor(s); defaults to `null`
 * 
 * @returns {Object|null} either (a) a plugin class, or (b) null if plugin name is not known
 */
export const tryInitPluginManager = (pluginName, cache = null, opts = null) => {
  if (!stringHasChars(pluginName)) {
    return null;
  }

  const hasCache = isRecordType(cache);
  pluginName = pluginName.trim();

  if (hasCache && cache.hasOwnProperty(pluginName)) {
    return cache[pluginName];
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
    opts = isRecordType(opts) && opts.hasOwnProperty(pluginName) && Array.isArray(opts[pluginName])
      ? opts[pluginName]
      : [];

    hnd = new hnd(...opts);
  }

  if (hasCache) {
    cache[pluginName] = hnd;
  }

  return hnd;
};

/**
 * @desc initialises plugin managers for page components
 */
export const managePlugins = (parent = document, options = { }) => {
  const elements = parent.querySelectorAll('[data-plugins]');

  const handlers = { };
  for (let i = 0; i < elements.length; ++i) {
    const element = elements[i];

    let plugins = element.getAttribute('data-plugins');
    if (!stringHasChars(plugins)) {
      continue;
    }

    plugins = plugins.split(/(?:,|;)\s*/);
    for (let j = 0; j < plugins.length; ++j) {
      const hnd = tryInitPluginManager(plugins[j], handlers, options);
      if (!hnd) {
        continue;
      }

      hnd.addElement(element);
    }
  }

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
          const hnd = tryInitPluginManager(plugins[j], handlers, options);
          if (!hnd) {
            continue;
          }

          hnd.addElement(node);
        }
      }
    }
  });

  observer.observe(parent, { subtree: true, childList: true });
  return observer.disconnect();
};
