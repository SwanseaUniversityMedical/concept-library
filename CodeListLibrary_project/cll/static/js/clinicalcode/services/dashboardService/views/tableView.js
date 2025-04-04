import * as Const from '../constants.js';

/**
 * Class to dynamically render data model tables
 * 
 * @class
 * @constructor
 */
export class TableView {
  /**
   * @desc default constructor props
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   * @property {string}                                     url                    Table query URL
   * @property {object}                                     [state={}]             Current table state; defaults to empty state; defaults to an empty object
   * @property {string|HTMLElement}                         [element='#tbl']       The table view root element container; defaults to `#tbl`
   * @property {Record<string, Record<string, HTMLElement>} [templates=null]       Optionally specify the templates to be rendered (will collect from page otherwise); defaults to `null`
   * @property {(ref, trg) => void}                         [displayCallback=null] Optionally specify the display callback (used to open view panel); defaults to `null`
   */
  static #DefaultOpts = {
    url: null,
    state: {},
    element: null,
    templates: null,
    displayCallback: null,
  };

  /**
   * @desc
   * @type {HTMLElement}
   * @public
   */
  element = null;

  /**
   * @desc
   * @type {object}
   * @private
   */
  #props = { };

  /**
   * @desc
   * @type {object}
   * @private
   */
  #queryState = {
    search: '',
    page: 1,
  };

  /**
   * @desc
   * @type {Record<string, Record<string, HTMLElement>}
   * @private
   */
  #templates = { };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = { };

  /**
   * @desc
   * @type {Array<Function>}
   * @private
   */
  #disposables = [];

  /**
   * @param {Record<string, any>} [opts] constructor arguments; see {@link TableView.#DefaultOpts}
   */
  constructor(opts) {
    opts = isRecordType(opts) ? opts : { };
    opts = mergeObjects(opts, TableView.#DefaultOpts, true);

    this.#initialise(opts);
  }


  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/
  dispose() {
    let disposable;
    for (let i = this.#disposables.length; i > 0; i--) {
      disposable = this.#disposables.pop();
      if (typeof disposable !== 'function') {
        continue;
      }

      disposable();
    }
  }


  /*************************************
   *                                   *
   *            Renderables            *
   *                                   *
   *************************************/
  #clear() {
    const layout = this.#layout;
    layout.head.innerHTML = '';
    layout.body.innerHTML = '';
    layout.footer.innerHTML = '';
  }

  #render() {
    const url = this.#props.url;
    const layout = this.#layout;
    const element = this.element;
    const templates = this.#templates;

    let parameters = this.#queryState;
    if (parameters instanceof URLSearchParams) {
      parameters = '?' + parameters;
    } else if (isObjectType(parameters)) {
      parameters = '?' + new URLSearchParams(parameters);
    } else if (typeof parameters !== 'string') {
      parameters = '';
    }

    let spinners;
    let spinnerTimeout = setTimeout(() => {
      spinners = {
        load: startLoadingSpinner(element, true),
      };
    }, 200);

    this.#fetch(url + parameters)
      .then(res => res.json())
      .then(res => {
        const { detail, renderable, results } = res;
        const { form, fields } = renderable;
        this.#clear();

        let headContent = [];
        for (let i = 0; i < fields.length; ++i) {
          const field = fields[i];
          const column = form[field];
          headContent.push(createElement('td', { text: column.label ?? field }));
        }
  
        headContent = createElement('tr', {
          childNodes: headContent,
          parent: layout.head,
        });

        const bodyContent = [];
        for (let i = 0; i < results.length; ++i) {
          const row = results[i];
          const items = fields.map((k, j) => {
            const field = fields?.[j];
            const column = form?.[field];
            const strDisplay = column?.str_display;

            let trg = row[k];
            if (typeof strDisplay === 'string') {
              if (isRecordType(trg)) {
                trg = trg[strDisplay] ?? trg;
              } else if (Array.isArray(trg)) {
                trg = trg.map(x => isRecordType(x) ? (x[strDisplay] ?? x) : x).join(', ');
              }
            } else if (Array.isArray(trg)) {
              trg = trg.join(', ');
            }

            if (j === 0) {
              return createElement('td', {
                childNodes: createElement('a', {
                  text: trg,
                  attributes: {
                    'role': 'button',
                    'target': '_blank',
                    'tabindex': '0',
                    'aria-label': 'View Item',
                    'data-for': 'display',
                    'data-ref': k,
                    'data-trg': trg,
                    'data-controller': 'filter',
                  }
                })
              });
            }
  
            return createElement('td', { text: trg });
          });

          bodyContent.push(createElement('tr', {
            childNodes: items,
            parent: layout.body,
          }));
        }
  
        // Init pagination
        const pageControls = [];
        const pageRangeLen = detail.pages.length;
        if (pageRangeLen > 0) {
          for (let i = 0; i < pageRangeLen; ++i) {
            let item = detail.pages[i];
            if (typeof item === 'number') {
              pageControls.push(interpolateString(templates.pages.button.innerHTML.trim(), {
                page: item,
                cls: detail.page === item ? 'is-active' : '',
              }));
            } else if (item === 'divider') {
              pageControls.push(templates.pages.divider.innerHTML.trim());
            }
          }
        } else {
          pageControls.push(templates.pages.empty.innerHTML.trim());
        }
  
        composeTemplate(templates.pages.controls, {
          params: {
            page: detail.page.toLocaleString(),
            totalPages: detail.total_pages.toLocaleString(),
            hasNext: detail.has_next,
            hasPrevious: detail.has_previous,
            startIdx: ((detail.page - 1)*detail.page_size + 1).toLocaleString(),
            endIdx: Math.min(detail.page*detail.page_size + 1, detail.max_results).toLocaleString(),
            rowCount: detail.max_results.toLocaleString(),
            content: pageControls.join('\n'),
          },
          parent: layout.footer,
        });
      })
      .catch(e => {
        console.error(`[TableView] Failed to load form:\n\n- Props: ${this.#props}- with err: ${e}\n`);

        window.ToastFactory.push({
          type: 'warning',
          message: 'Failed to load view, please try again.',
          duration: 4000,
        });
      })
      .finally(() => {
        if (!spinners) {
          clearTimeout(spinnerTimeout);
        }
        spinners?.load?.remove?.();
      });
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #searchHandle(e) {
    const searchBox = this.#layout.searchBox;
    const queryState = this.#queryState;

    const field = searchBox.getAttribute('data-field');
    if (!stringHasChars(field)) {
      return;
    }

    let value = searchBox.value;
    if (!stringHasChars(value)) {
      value = null;
    }

    const prevValue = queryState.hasOwnProperty(field) ? queryState[field] : null;
    if (prevValue === value) {
      return;
    }

    if (e.type === 'keyup') {
      const code = e.keyIdentifier || e.which || e.keyCode;
      if (code !== Const.CLU_DASH_KEYCODES.ENTER) {
        return;
      }
    }

    if (value === null || typeof value === 'undefined') {
      delete queryState[field];
    } else {
      queryState[field] = value;
    }
    window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    this.#render();
  }

  #pageHandle(e) {
    const queryState = this.#queryState;

    const evTarget = e.target;
    if (!evTarget.matches('[data-field="page"]:not(.disabled):not(:disabled):not([disabled="true"])')) {
      return;
    }

    const field = evTarget.getAttribute('data-field');
    if (field !== 'page') {
      return;
    }

    e.stopPropagation();
    e.preventDefault();

    let value = evTarget.getAttribute('data-value');
    if (value === Const.CLU_DASH_TARGETS.NEXT || value === Const.CLU_DASH_TARGETS.PREVIOUS) {
      const offset = value === Const.CLU_DASH_TARGETS.NEXT ? 1 : -1;
      const current = queryState.hasOwnProperty(field) ? queryState[field] : 1;
      value = current + offset;
    }

    value = parseInt(value);
    if (isNaN(value)) {
      return;
    }

    queryState[field] = value;
    window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
    this.#render();
  }

  #displayHandle(e) {
    const evTarget = e.target;
    if (!evTarget.matches('a[data-controller="filter"][data-for="display"]:not(:disabled):not(.disabled)')) {
      return;
    }

    const evRef = evTarget.getAttribute('data-ref');
    const evTrg = evTarget.getAttribute('data-trg');
    if (!stringHasChars(evRef) || !stringHasChars(evTrg)) {
      return;
    }

    e.stopPropagation();
    e.preventDefault();

    const callback = this.#props.displayCallback;
    if (typeof callback !== 'function') {
      return;
    }

    callback(evRef, evTrg);
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  #fetch(url, opts = {}) {
    const token = this.#props.state.token;
    opts = mergeObjects(
      isObjectType(opts) ? opts : {},
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

    return fetch(url, opts);
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise(opts) {
    if (!stringHasChars(opts.url)) {
      throw new Error('InitError: Failed to resolve TableView target URL');
    }

    let element = opts.element;
    delete opts.element;

    if (typeof element === 'string') {
      element = document.querySelector(element);
    }

    if (!isHtmlObject(element)) {
      throw new Error('InitError: Failed to resolve TableView element');
    }

    let templates = opts.templates;
    if (isRecordType(templates)) {
      this.#templates = templates;
      delete opts.templates;
    } else {
      let elem, view, group, name;
      const tmpl = document.querySelectorAll('template[data-for="dashboard"]');
      for (let i = 0; i < tmpl.length; ++i) {
        elem = tmpl[i];
        name = elem.getAttribute('data-name');
        view = elem.getAttribute('data-view');
        if (!stringHasChars(view)) {
          view = 'base';
        }

        group =  this.#templates?.[view];
        if (!group) {
          group = { };
          this.#templates[view] = group;
        }

        group[name] = elem;
      }

      templates = this.#templates;
    }

    this.#props = opts;
    this.element = element;

    const layout = this.#layout;
    const queryState = this.#queryState;
    composeTemplate(templates.base.table, {
      params: {
        query: queryState.search ?? '',
      },
      parent: element,
      render: (elems) => {
        const [ searchContainer, table ] = elems;

        const head = table.querySelector('thead');
        const body = table.querySelector('tbody');
        const footer = table.querySelector('footer');
        layout.head = head;
        layout.body = body;
        layout.table = table;
        layout.footer = footer;

        const searchBox = searchContainer.querySelector('#searchbar');
        const searchBtn = searchContainer.querySelector('#searchbar-icon-btn');
        layout.searchBox = searchBox;
        layout.searchBtn = searchBtn;
        layout.searchContainer = searchContainer;

        this.#initEvents();
        this.#render();
      },
    });
  }

  #initEvents() {
    const pageHnd = this.#pageHandle.bind(this);
    const searchHnd = this.#searchHandle.bind(this);
    const displayHnd = this.#displayHandle.bind(this);

    const { body, footer, searchBox, searchBtn } = this.#layout;
    body.addEventListener('click', displayHnd);
    footer.addEventListener('click', pageHnd);
    searchBox.addEventListener('keyup', searchHnd);
    searchBtn.addEventListener('click', searchHnd);

    this.#disposables.push(() => {
      body.removeEventListener('click', displayHnd);
      footer.removeEventListener('click', pageHnd);
      searchBox.removeEventListener('keyup', searchHnd);
      searchBtn.removeEventListener('click', searchHnd);
    });
  }
};
