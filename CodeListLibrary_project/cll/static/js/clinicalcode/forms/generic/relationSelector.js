import DebouncedTask from '../../components/tasks/debouncedTask.js';

/**
 * Class to manage related entity selector component(s)
 * 
 * @class
 * @constructor
 */
export default class RelationSelector {
  /**
   * @desc default constructor options
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   */
  static #DefaultOpts = {
    /**
     * @desc describes a set of props assoc. the field represented by this component
     * @type {Record<string, any>}
     */
    properties: {
      /**
       * @desc the fetch request target, i.e. the endpoint from which we retrieve results
       * @type {string}
       */
      lookup: '/api/v1/phenotypes/',
      /**
       * @desc describes how to generate a label for a selected item
       * @type {Array<string>}
       */
      display: ['id', 'history_id', 'name'],
      /**
       * @desc describes how to generate a label for an entity search result
       * @type {Array<string>}
       */
      labeling: ['phenotype_id', 'name'],
      /**
       * @desc describes how to generate a reference from the entity's detail
       * @type {Array<string>}
       */
      reference: ['phenotype_id', 'phenotype_version_id'],
      /**
       * @desc describes how references should be stored in the resulting data (mapped by index) 
       * @type {Array<string>}
       */
      storage: ['id', 'history_id'],
      /**
       * @desc the delay duration, in milliseconds, before we attempt to fetch results
       * @type {number}
       */
      searchDelay: 250,
      /**
       * @desc the minimum num. of chars required before querying the results endpoint
       * @note excludes whitespace-only strings
       * @type {number}
       */
      searchMinChars: 1,
    },
    /**
       * @desc 
       * @type {Record<string, number>}
       * @see {module:utils.fetchWithCtrl}
     */
    requestCtrl: {
      /**
       * @desc fetch req timeout (in seconds)
       * @type {number}
       */
      timeout: 5,
      /**
       * @desc fetch req backoff factor for delay on failed retry attempts
       * @type {number}
       */
      backoff: 50,
      /**
       * @desc max number of retry attempts on each search attempt
       * @type {number}
       */
      retries: 1,
    }
  };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = {};

  /**
   * @desc
   * @type {Record<string, Record<string, HTMLElement>>}
   * @private
   */
  #templates = {};

  /**
   * @desc
   * @type {string}
   * @private
   */
  #token = null;

  /**
   * @desc
   * @type {DebouncedTask}
   * @private
   */
  #searchTask = null;

  /**
   * @desc specifies a reference to the the object being edited
   * @type {string}
   * @private
   */
  #selfTarget = null;

  /**
   * @desc describes the state of the component, i.e. index of the active element within the dropdown selector and the resultset (if any)
   * @type {Record<string, any>}
   * @private
   */
  #state = {
    results: null,
    activeIndex: -1,
    activeObject: null,
  };

  /**
   * @param {HTMLElement}         element   the HTMLElement assoc. with this component
   * @param {Record<string, any>} fieldData specifies the initial value, properties, validation, and options of the component
   * @param {Record<string, any>} [opts]    optionally specify any additional component opts; see {@link RelationSelector.#DefaultOpts}
   */
  constructor(element, fieldData, opts) {
    let { value, properties, mapping } = isObjectType(fieldData) ? fieldData : { };
    mapping = isObjectType(mapping) ? mapping : { };
    properties = isObjectType(properties) ? properties : { };

    opts = isObjectType(opts) ? opts : {};
    opts.mapping = mergeObjects(
      isObjectType(opts.mapping)
        ? opts.mapping
        : { },
      mapping
    );
    opts.properties = mergeObjects(
      isObjectType(opts.properties) ? opts.properties : {},
      properties,
      false,
      true
    );

    opts = mergeObjects(opts, RelationSelector.#DefaultOpts, false, true);

    const lookup = opts.properties.lookup;
    opts.properties.lookup = stringHasChars(lookup)
      ? RelationSelector.#GetBrandedLookup(lookup)
      : '';

    this.data = Array.isArray(value) ? value : [];
    this.props = opts;
    this.dirty = false;
    this.element = element;

    const obj = this.props.object;
    if (isObjectType(obj)) {
      const { reference, storage } = this.props.properties;

      let comp = !isNullOrUndefined(obj?.[storage[0]]) ? obj[storage[0]] : '';
      for (let i = 1; i < Math.min(reference.length, storage.length); ++i) {
        if (obj?.[storage[i]]) {
          comp += '/' + obj[storage[i]];
        }
      }

      this.#selfTarget = comp;
    }

    this.#token = getCookie('csrftoken');
    this.#searchTask = new DebouncedTask(this.#fetchResults.bind(this), opts.properties.searchDelay, true);

    this.#initialise();
  }

  /*************************************
   *                                   *
   *              Static               *
   *                                   *
   *************************************/
  static #GetBrandedLookup(url, keepParameters = false) {
    if (typeof url !== 'string' || !stringHasChars(url)) {
      const details = typeof url === 'string'
        ? `a "${typeof url}`
        : (url.length && isStringWhitespace(url) ? 'a whitespace-only "string"' : 'an empty "string"');

      throw new Error(`[RelationSelector::GetBrandedLookup] Invalid lookup URL, expected a valid URL string but got ${details}; where URL<value="${url}">`);
    }

    const host = getBrandedHost();
    url = `${host}/${url}`;
    url = url.replace(/(?<!:\/)(?<=\/)(?:\/{1})|(.)(?:\/+$)/g, '$1');

    if (!stringHasChars(url)) {
      const details = url.length && isStringWhitespace(url) ? 'a whitespace-only "string"' : 'an empty "string"';
      throw new Error(`[RelationSelector::GetBrandedLookup] Invalid lookup URL, expected non-empty string but got ${details}; where URL<value="${url}">`);
    }

    try {
      url = new URL(url);
    } catch (e) {
      throw new Error(`[RelationSelector::GetBrandedLookup] Failed to parse the provided lookup URL<value="${url}"> with err:\n\n${e}`);
    }

    if (keepParameters) {
      return url.href;
    }

    return url.origin + url.pathname;
  }


  /*************************************
   *                                   *
   *              Getter               *
   *                                   *
   *************************************/
  /**
   * @returns {Array<Record<string, string|number>} an array describing the entities contained by this component
   */
  getData() {
    return this.data;
  }

  /**
   * @returns {HTMLElement} the assoc. element
   */
  getElement() {
    return this.element;
  }

  /**
   * @returns {bool} returns the dirty state of this component
   */
  isDirty() {
    return this.dirty;
  }


  /*************************************
   *                                   *
   *              Setter               *
   *                                   *
   *************************************/
  /**
   * @desc informs the top-level parent that we're dirty and updates our internal dirty state
   * 
   * @return {this}
   */
  makeDirty() {
    window.entityForm.makeDirty();
    this.dirty = true;
    return this;
  }


  /*************************************
   *                                   *
   *            Renderables            *
   *                                   *
   *************************************/
  /**
   * @desc toggles the expansion of the result section
   * 
   * @return {this}
   */
  #toggleResultVis(val) {
    const layout = this.#layout;
    if (!layout) {
      return;
    }

    layout.search.setAttribute('aria-expanded', val)
    return this;
  }

  /**
   * @desc toggles the page content presentation section 
   * 
   * @return {this}
   */
  #toggleLayoutContentVis(val) {
    const layout = this.#layout;
    if (!layout) {
      return;
    }

    if (val) {
      layout.contentGroup.classList.add('show');
      layout.noneAvailable.classList.remove('show');
    } else {
      layout.noneAvailable.classList.add('show');
      layout.contentGroup.classList.remove('show');
    }

    return this;
  }

  #renderInfobox(show = false, details = null, isLoading = false) {
    const layout = this.#layout;
    if (!layout) {
      return;
    }

    const { loader, infobox, infolabel } = layout;
    if (!show) {
      infobox.classList.remove('entity-dropdown__infobox--show');
      return;
    }

    let labelContent;
    clearAllChildren(infolabel);

    if (isObjectType(details) && details?.label && stringHasChars(details?.label)) {
      labelContent = details.label;
    } else if (typeof details === 'string' && stringHasChars(details)) {
      labelContent = details;
    }

    if (!!labelContent) {
      createElement('p', { parent: infolabel, text: labelContent, className: 'entity-dropdown__infobox-label' });
    }

    if (isLoading) {
      loader.classList.add('bounce-loader--show');
    } else {
      loader.classList.remove('bounce-loader--show');
    }

    infobox.classList.add('entity-dropdown__infobox--show');
    return this;
  }

  #renderResults(results, isLoading = false) {
    // i.e. render all results
    /*
      <template data-name="item" data-view="base">
      - ${ref}   -> id
      - ${index} -> list index
      - ${label} -> text content
    */

    const props = this.props;
    const state = this.#state;
    const layout = this.#layout;
    const templates = this.#templates;
    state.results = results;
    state.activeIndex = -1;
    state.activeObject = null;
  
    clearAllChildren(layout.results, '.entity-dropdown__item');

    const data = isObjectType(results) ? results?.data : null;
    if (!data) {
      this.#renderInfobox(true, null, true);
    } else {
      let { resultSz, totalSz } = results.info;

      const wasEqual = resultSz === totalSz;
      const lblTarget = props.properties.labeling;
      const refTarget = props.properties.reference;
      for (let i = 0; i < data.length; ++i) {
        const res = data[i];

        let ref = res[refTarget[0]];
        for (let i = 1; i < refTarget.length; ++i) {
          ref += '/' + res[refTarget[i]];
        }

        if (this.#selfTarget === ref || this.getSelectedItem(ref)) {
          resultSz -= 1;
          continue;
        }

        let label = res[lblTarget[0]];
        for (let i = 1; i < lblTarget.length; ++i) {
          label += (i === 1 ? '/' : ' - ') + res[lblTarget[i]];
        }

        composeTemplate(templates.results.item, {
          params: {
            ref: ref,
            index: i,
            label: label,
          },
          parent: layout.results,
        });
      }

      if (resultSz > 0) {
        if (wasEqual) {
          totalSz = Math.min(resultSz, totalSz);
        }

        results.info.label = `Showing ${resultSz.toLocaleString()} of ${totalSz.toLocaleString()} result(s)`;
      } else {
        results.info.label = `No known results for these search terms`;
      }

      this.#renderInfobox(true, results.info, false);
    }

    const isExpanded = results || isLoading;
    if (!isExpanded) {
      state.results = null;
      state.activeIndex = -1;
      state.activeObject = null;
    }
    this.#toggleResultVis(isExpanded);
  }

  #renderLayout() {
    const data = this.data;
    const props = this.props;
    const hasData = data.length > 0;
    this.#toggleLayoutContentVis(hasData);

    const layout = this.#layout;
    clearAllChildren(layout.contentList, '.entity-selector-group__item');

    // Draw children
    if (hasData) {
      const templates = this.#templates;
      const dspTarget = props.properties.display;
      const srcTarget = props.properties.storage;
      const refTarget = props.properties.reference;

      let item, comp, label;
      for (let i = 0; i < data.length; ++i) {
        item = data[i];

        comp = item?.__comp;
        if (!comp) {
          comp = item[srcTarget[0]];
          for (let i = 1; i < Math.min(refTarget.length, srcTarget.length); ++i) {
            comp += '/' + item[srcTarget[i]];
          }
  
          item.__comp = comp;
        }

        label = item?.__label;
        if (!label) {
          label = item[dspTarget[0]];
          for (let i = 1; i < dspTarget.length; ++i) {
            label += (i === 1 ? '/' : ' - ') + item[dspTarget[i]];
          }
  
          item.__label = label;
        }

        composeTemplate(templates.content.item, {
          params: {
            ref: comp,
            label: label,
          },
          parent: layout.contentList,
        });
      }
    }
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  getSelectedItem(ref) {
    const props = this.props;
    const selected = this.data;
    const srcTarget = props.properties.storage;
    const refTarget = props.properties.reference;
    return selected.find(x => {
      let comp = x?.__comp;
      if (!comp) {
        let comp = x[srcTarget[0]];
        for (let i = 1; i < Math.min(refTarget.length, srcTarget.length); ++i) {
          comp += '/' + x[srcTarget[i]];
        }

        x.__comp = comp;
      }

      return ref === comp;
    });
  }

  #handleFetchAccept(res) {
    if (!res.ok) {
      throw new Error(`Failed request with Status<code: ${res.status}>`, { cause: 'status' });
    }

    return true;
  }

  #handleFetchResolve(res) {
    const layout = this.#layout;
    if (!layout) {
      return;
    }

    if (!layout.search.contains(document.activeElement)) {
      return;
    }

    const {
      data        = [],
      page_size   = 20,
      total_pages = 1
    } = res;

    if (!Array.isArray(data)) {
      throw new Error(`Failed to retrieve results`);
    }

    let totalSz, resultSz;
    resultSz = data.length;
    if (typeof page_size === 'number' && typeof total_pages === 'number') {
      totalSz = total_pages > 1 ? page_size*total_pages : Math.min(page_size, resultSz);
    } else {
      totalSz = resultSz;
    }

    this.#renderResults({
      data: data,
      info: { totalSz, resultSz },
      hasResults: resultSz > 0,
    });
  }

  #handleFetchErrors(err, url) {
    const fieldName = this.element.getAttribute('data-name');

    let msg;
    if (!err || err instanceof Error) {
      const cause = err?.cause;
      if (getObjectClassName(cause).match(/(object|string)/gi)) {
        if (typeof cause === 'string') {
          switch (cause) {
            case 'unknown':
            case 'timeout':
              msg = `[${fieldName}] ${e.message}`;
              break;

            default:
              break;
          }
        } else if (isObjectType(cause)) {
          // Future custom err handling if required???

        }
      }
    }

    msg = stringHasChars(msg)
      ? msg
      : `[${fieldName}] It looks like we failed to get the results, please try again in a moment.`;

    window.ToastFactory.push({
      type: 'danger',
      message: msg,
      duration: 4000,
    });

    console.error(`[RelationSelector->fetchResults] Failed to fetch results from URL<${url}> with err:\n\n${err}`);
  }

  #fetchResults({ url, opts, ctrl, parameters } = {}) {
    const props = this.props;

    if (!!parameters && parameters instanceof URLSearchParams) {
      parameters = '?' + parameters;
    } else if (isObjectType(parameters)) {
      parameters = '?' + new URLSearchParams(parameters);
    } else {
      parameters = '';
    }

    url = typeof url === 'string'
      ? url + parameters
      : props.properties.lookup + parameters;

    const token = this.#token;
    ctrl = mergeObjects(isObjectType(ctrl) ? ctrl : { }, props.requestCtrl, false, true);
    opts = mergeObjects(
      isObjectType(opts) ? opts : { },
      {
        method: 'GET',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      },
      false,
      true
    );

    const errorHandler = opts.errorHandler;
    const resultHandler = opts.resultHandler;
    return fetchWithCtrl(url, opts, ctrl)
      .then(res => res.json())
      .then(res => {
        if (typeof resultHandler === 'function') {
          resultHandler?.(res);
        } else if (resultHandler !== null) {
          this.#handleFetchResolve(res);
        }
      })
      .catch(err => {
        if (typeof errorHandler === 'function') {
          errorHandler?.(err, url)
        } else if (errorHandler !== null) {
          this.#handleFetchErrors(err, url);
        }
      });
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #initEvents() {
    const layout = this.#layout;
    window.addEventListener('focusout', this.#handleBlur.bind(this));
    document.addEventListener('click', this.#handleClick.bind(this));

    const inputbox = layout.inputbox;
    inputbox.addEventListener('input', this.#handleInput.bind(this));
    inputbox.addEventListener('keyup', this.#handleInputKeyUp.bind(this));
    inputbox.addEventListener('keydown', this.#handleInputKeyDown.bind(this));
  }

  #handleClick(e) {
    const state = this.#state;
    const props = this.props;
    const layout = this.#layout;
    const data = isObjectType(state?.results) && Array.isArray(state?.results?.data)
      ? state.results.data
      : null;

    if (!layout) {
      return;
    }

    const { target } = e;
    const { results, inputbox, contentList } = layout;
    if (data && results.contains(target) && target.matches('[data-action="select"]')) {
      let index = target.getAttribute('data-index');
      index = parseInt(index);
      if (typeof index !== 'number' || isNaN(index)) {
        return;
      }
  
      const srcTarget = props.properties.storage;
      const refTarget = props.properties.reference;
      const selection = data[index];
      this.#searchTask.clear();
      this.#renderResults(null, false);
  
      const ref = { };
      for (let i = 0; i < srcTarget.length; ++i) {
        if (refTarget?.[i]) {
          ref[srcTarget[i]] = selection[refTarget[i]];
        } else {
          ref[srcTarget[i]] = selection[srcTarget[i]];
        }
      }
      this.data.push(ref);
      this.#renderLayout();
      this.makeDirty();

      inputbox.focus();
      inputbox.blur();
      inputbox.value = '';
    } else if (contentList.contains(target) && target.matches('[data-fn="button"][data-action="remove"]')) {
      const ref = target.getAttribute('data-ref');
      if (!stringHasChars(ref)) {
        return;
      }

      const item = this.getSelectedItem(ref);
      const index = this.data.findIndex(x => x === item);
      if (index >= 0) {
        this.data.splice(index, 1);
        this.makeDirty();
        this.#renderLayout();
      }
    }
  }

  #handleBlur(e) {
    const layout = this.#layout;
    if (!layout) {
      return;
    }

    const { search } = layout;
    const { relatedTarget } = e;
    if (!relatedTarget || !search.contains(relatedTarget)) {
      this.#state.results = null;
      this.#state.activeIndex = -1;
      this.#state.activeObject = null;
      this.#searchTask.clear();
      this.#renderResults(null, false);
    }
  }

  #handleInput(e) {
    const value = e.target.value;
    const props = this.props?.properties;
    const minSearchChars = typeof props?.searchMinChars === 'number' ? props?.searchMinChars : 0;
    if (!stringHasChars(value) || (minSearchChars && value.length < minSearchChars)) {
      this.#renderResults(null, false);
      return;
    }
    this.#renderResults(null, true);

    this.#searchTask({
      ctrl: { beforeAccept: this.#handleFetchAccept.bind(this) },
      parameters: { search: value }
    });
  }

  #handleInputKeyDown(e) {
    const state = this.#state;
    const props = this.props?.properties;
    const layout = this.#layout;
    const inputbox = e.target;
    if (!layout) {
      return;
    }

    const key = e.key;
    const data = isObjectType(state?.results) && Array.isArray(state?.results?.data)
      ? state.results.data
      : null;

    switch (key) {
      case 'ArrowUp': {
        e.preventDefault();

        if (data) {
          const len = data.length;
          state.activeIndex = state.activeIndex < 1 ? len - 1 : ((state.activeIndex + 1)%len + len)%len;
        } else {
          state.activeIndex = -1;
        }
      } break;

      case 'ArrowDown': {
        e.preventDefault();

        if (data) {
          const len = data.length;
          state.activeIndex = state.activeIndex < 1 ? 0 : ((state.activeIndex - 1)%len + len)%len;
        } else {
          state.activeIndex = -1;
        }
      } break;

      case 'Enter': {
        if (state.activeObject && state.activeIndex >= 0) {
          const srcTarget = props.storage;
          const refTarget = props.reference;
          const selection = state.activeObject.selection;
          this.#searchTask.clear();
          this.#renderResults(null, false);

          const ref = { };
          for (let i = 0; i < srcTarget.length; ++i) {
            if (refTarget?.[i]) {
              ref[srcTarget[i]] = selection[refTarget[i]];
            } else {
              ref[srcTarget[i]] = selection[srcTarget[i]];
            }
          }
          this.data.push(ref);
          this.#renderLayout();
          this.makeDirty();

          inputbox.blur();
          inputbox.value = '';
        }
      } break;

      case 'Escape':
        this.#searchTask.clear();
        this.#renderResults(null, false);
        return;

      default:
        return;
    }

    if (data && state.activeIndex >= 0) {
      if (state?.activeObject?.element) {
        state.activeObject.element.setAttribute('aria-selected', false);
      }

      const elem = layout.results.querySelector(`[data-index="${state.activeIndex}"]`);
      if (elem) {
        elem.setAttribute('aria-selected', true);
        scrollContainerTo(layout.results, elem);
      }

      state.activeObject = {
        element: elem,
        selection: data[state.activeIndex],
      };
    } else if (state.activeObject) {
      const elem = state.activeObject.element;
      if (elem) {
        elem.setAttribute('aria-selected', false);
        layout.results.scrollTo({ top: 0, left: 0, behavior: 'instant' });
      }
      state.activeObject = null;
    }
  }

  #handleInputKeyUp(e) {
    const key = e.key;
    if (key === 'Enter') {
      e.preventDefault();
      return;
    }
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise() {
    const elem = this.element;
    const layout = this.#layout;
    elem.querySelectorAll('[data-area]').forEach(v => {
      const role = v.getAttribute('data-area');
      if (stringHasChars(role)) {
        layout[role] = v;
      }
    });

    const templates = this.#templates;
    elem.querySelectorAll('template[data-name]').forEach(v => {
      let name = v.getAttribute('data-name');
      let view = v.getAttribute('data-view');
      if (!stringHasChars(view)) {
        view = 'base';
      }

      let group =  templates?.[view];
      if (!group) {
        group = { };
        templates[view] = group;
      }

      group[name] = v;
    });

    this.#initEvents();
    this.#renderLayout();
  }
};
