/**
 * CSEL_VIEWS
 * @desc describes the view states of this component
 */
const CSEL_VIEWS = {
  // The search view whereby users can select Concepts
  SEARCH: 0,

  // The current selection view, only accessible when allowMultiple flag is set to true
  SELECTION: 1,
};

/**
 * CSEL_EVENTS
 * @desc used internally to track final state of dialogue
 */
const CSEL_EVENTS = {
  // When a dialogue is cancelled without changes
  CANCELLED: 0,

  // When a dialogue is confirmed, with or without changes
  CONFIRMED: 1,
};

/**
 * CSEL_BEHAVIOUR
 * @desc describes base behaviour of the service
 */
const CSEL_BEHAVIOUR = {
  // Defines cache time for get requests (ms)
  CACHE_TIME: 300_000, // i.e. 5 minutes

  // Defines the output format behaviour of datetime objects
  DATE_FORMAT: 'YYYY-MM-DD',

  // Describes keycodes for filter-related events
  KEY_CODES: {
    ENTER: 13,
  },

  // Describes non-numerical data-value targets for pagination buttons
  PAGINATION: {
    NEXT: 'next',
    PREVIOUS: 'previous',
  },

  // Describes the acceptable date formats when parsing
  ACCEPTABLE_DATE_FORMAT: ['DD-MM-YYYY', 'MM-DD-YYYY', 'YYYY-MM-DD'],

  // Describes the query URL
  QUERY_URL: '/query',

  // Describes endpoints used to ret. data
  ENDPOINTS: {
    SPECIFICATION: 'get_filters',
    RESULTS: 'get_results',
  }
}

/**
 * CSEL_OPTIONS
 * @desc Available options for this component,
 *       where each of the following options are used as default values
 *       and are appended automatically if not overriden.
 */
const CSEL_OPTIONS = {
  // Which template to query when retrieving accessible entities
  template: 1,

  // Related entity ids to filter the entity from results
  entity_id: null,
  entity_history_id: null,

  // Allow more than a single Concept to be selected
  allowMultiple: true,

  // Whether to remember the selection when previously opened
  //  [!] Note: Only works when allowMultiple flag is set to true
  maintainSelection: true,

  // Flag to determine whether we scroll to the top of the result page when pagination occurs
  scrollOnResultChange: true,

  // The title of the prompt
  promptTitle: 'Import Concepts',

  // The confirm button text
  promptConfirm: 'Confirm',

  // The cancel button text
  promptCancel: 'Cancel',

  // The size of the prompt (ModalFactory.ModalSizes.%s, i.e., {sm, md, lg})
  promptSize: 'lg',

  // The message shown when no items are selected
  noneSelectedMessage: 'You haven\'t selected any Concepts yet',

  // Whether to maintain applied filters when user enters/exits the search dialogue
  maintainFilters: true,

  // Filters to ignore (by field name)
  ignoreFilters: [ ],

  // Force context of filters
  forceFilters: { },

  // Which filters, if any, to apply to children
  childFilters: ['coding_system'],

  // Whether to cache the resulting queries for quicker,
  // albeit possibly out of date, Phenotypes and their assoc. Concepts
  useCachedResults: false,
};

/**
 * CSEL_BUTTONS
 * @desc The styleguide for the prompt's buttons
 */
const CSEL_BUTTONS = {
  CONFIRM: '<button class="primary-btn text-accent-darkest bold secondary-accent" aria-label="Confirm" id="confirm-button"></button>',
  CANCEL: '<button class="secondary-btn text-accent-darkest bold washed-accent" aria-label="Cancel" id="reject-button"></button>',
};

/**
 * CSEL_INTERFACE
 * @desc defines the HTML used to render the selection interface
 */
const CSEL_INTERFACE = {
  // Main dialogue modal
  DIALOGUE: ' \
  <div class="target-modal target-modal-${promptSize}" id="${id}" aria-hidden="${hidden}"> \
    <div class="target-modal__container"> \
      <div class="target-modal__header"> \
        <h2 id="target-modal-title">${promptTitle}</h2> \
      </div> \
      <div class="target-modal__body" id="target-modal-content"> \
      </div> \
    </div> \
  </div>',

  // Tabbed views when allowMultiple flag is active
  TAB_VIEW: ' \
  <div class="tab-view" id="tab-view"> \
    <div class="tab-view__tabs tab-view__tabs-z-buffer"> \
      <button aria-label="tab" id="SEARCH" class="tab-view__tab active">Search Concepts</button> \
      <button aria-label="tab" id="SELECTION" class="tab-view__tab">Selected Concepts</button> \
    </div> \
    <div class="tab-view__content" id="tab-content"> \
    </div> \
  </div>',

  SELECTION_VIEW: ' \
  <div class="detailed-input-group fill no-margin"> \
    <div class="detailed-input-group__header"> \
      <div class="detailed-input-group__header-item"> \
        <p class="detailed-input-group__description">Your currently selected items:</p> \
      </div> \
    </div> \
    <section class="detailed-input-group__none-available" id="no-items-selected"> \
      <p class="detailed-input-group__none-available-message">${noneSelectedMessage}</p> \
    </section> \
    <fieldset class="code-search-group indented scrollable slim-scrollbar" id="item-list"> \
    </fieldset> \
  </div>',

  // Base search view
  SEARCH_VIEW: ' \
  <div class="search-page as-selection" id="selection-search"> \
    <aside class="selection-filters"> \
      <div class="selection-filters__header"> \
        <h3>Filter By</h3> \
        <div class="selection-filters__header-options"> \
          <button class="tertiary-btn text-accent-darkest bubble-accent" id="reset-filter-btn"> \
            Reset \
          </button> \
        </div> \
      </div> \
      <div class="selection-filters__container slim-scrollbar" id="search-filters"> \
      </div> \
    </aside> \
    <section class="entity-search-results entity-search-results--constrained"> \
      <div class="entity-search-results__header"> \
        <div class="entity-search-results__header-results" id="search-response-header"> \
          <h4>Results</h4> \
          <p></p> \
        </div> \
        <div class="entity-search-results__header-modifiers"> \
          <div class="selection-group"> \
            <p class="selection-group__title">Order By:</p> \
            <select id="order-by-filter" placeholder-text="By Relevance" data-element="dropdown" data-field="order_by" data-class="option"> \
              <option value="1" class="dropdown-selection__list-item" selected>Relevance</option> \
              <option value="2" class="dropdown-selection__list-item">Created (Asc)</option> \
              <option value="3" class="dropdown-selection__list-item">Created (Desc)</option> \
              <option value="4" class="dropdown-selection__list-item">Updated (Asc)</option> \
              <option value="5" class="dropdown-selection__list-item">Updated (Desc)</option> \
            </select> \
          </div> \
        </div> \
      </div> \
      <div class="entity-search-results__container scrollable slim-scrollbar" id="search-response-content"> \
      </div> \
      <div class="pagination-box push-bottom" id="search-pagination-area"> \
      </div> \
    </section> \
  </div>',

  // Search view pagination controls
  SEARCH_PAGINATION: ' \
  <section class="pagination-container" data-field="page" data-class="pagination" data-value="${page}"> \
    <div class="pagination-container__details"> \
      <p class="pagination-container__details-number"><span id="page-number">${page}</span> / <span id="page-total">${page_total}</span></p> \
    </div> \
    <ul class="pagination-container__previous"> \
      <li class="${prev_disabled ? "disabled" : ""}"> \
        <a data-value="previous" data-field="page" aria-label="Go Previous Page" tabindex="0" role="button">Previous</a> \
      </li> \
    </ul> \
    <ul class="pagination-container__next"> \
      <li class="${next_disabled ? "disabled" : ""}"> \
        <a data-value="next" data-field="page" aria-label="Go Next Page" tabindex="0" role="button">Next</a> \
      </li> \
    </ul> \
  </section>',

  // Search result card
  RESULT_CARD: ' \
  <article class="entity-card inactive" data-entity-id="${id}" data-entity-version-id="${history_id}" style="padding: 0;"> \
    <div class="entity-card__header"> \
      <div class="entity-card__header-item"> \
        <h3 class="entity-card__title">${id}/${history_id} - ${name}</h3> \
        <p class="entity-card__author">${author}</p> \
      </div> \
    </div> \
    <div class="entity-card__snippet"> \
      ${tags} \
      <div class="entity-card__snippet-datagroup" id="datagroup"> \
      </div> \
    </div> \
  </article>',

  // Card chip tags group
  CHIP_GROUP: ' \
  <div class="entity-card__snippet-tags"> \
    <div class="entity-card__snippet-tags-group" id="chip-tags"> \
      ${tags} \
    </div> \
  </div>',

  // Card chip for result card
  CHIP_TAGS: ' \
  <div class="meta-chip meta-chip-washed-accent"> \
    <span class="meta-chip__name meta-chip__name-text-accent-dark meta-chip__name-bold">${name}</span> \
  </div>',

  // Card accordian for children data
  CARD_ACCORDIAN: ' \
  <div class="fill-accordian" id="children-accordian-${id}" style="margin-top: 0.5rem"> \
    <input class="fill-accordian__input" id="children-${id}" name="children-${id}" type="checkbox" /> \
    <label class="fill-accordian__label" id="children-${id}" for="children-${id}" role="button" tabindex="0"> \
      <span>${title}</span> \
    </label> \
    <article class="fill-accordian__container" id="data" style="padding: 0.5rem;"> \
      ${content} \
    </article> \
  </div>',

  // Child selector for cards
  CHILD_SELECTOR: ' \
  <div class="checkbox-item-container ${!isSelector? "ignore-overflow" : ""}" id="${isSelector ? "child-selector" : "selected-item" }"> \
    <input id="${field}-${id}" aria-label="${title}" type="checkbox" ${checked ? "checked" : ""} data-index="${index}" \
      class="checkbox-item" data-id="${id}" data-history="${history_id}" \
      data-name="${title}" data-field="${field}" data-prefix="${prefix}" data-coding="${coding_system}"/> \
    <label for="${field}-${id}" class="constrained-filter-item">${title} [${coding_system}]</label> \
  </div>',
};

const CSEL_FILTER_COMPONENTS = {
  CHECKBOX: ' \
  <div class="checkbox-item-container"> \
    <input id="${field}-${pk}" aria-label="${value}" type="checkbox" class="checkbox-item" data-value="${pk}" data-name="${value}" data-class="checkbox" data-field="${field}" /> \
    <label for="${field}-${pk}" class="constrained-filter-item">${value}</label> \
  </div>',

  CHECKBOX_GROUP: ' \
  <div class="accordian" data-class="checkbox" data-field="${field}" data-type="${datatype}" \
    role="collapsible" tabindex="0" aria-labelledby="${title} Filters" aria-controls="filter-${field}"> \
    <input class="accordian__input" id="filter-${field}" name="filter-${field}" type="checkbox" /> \
    <label class="accordian__label" for="filter-${field}"> \
      <h4>${title}</h4> \
    </label> \
    <article class="accordian__container"> \
      <div class="filter-group filter-scrollbar"> \
      </div> \
    </article> \
  </div>',

  DATEPICKER_GROUP: ' \
  <div class="accordian" data-class="datepicker" data-field="${field}" data-type="${datatype}" \
    role="collapsible" tabindex="0" aria-labelledby="${title} Filters" aria-controls="filter-${field}"> \
    <input class="accordian__input" id="filter-${field}" name="filter-${field}" type="checkbox" /> \
    <label class="accordian__label" for="filter-${field}"> \
      <h4>${title}</h4> \
    </label> \
    <article class="accordian__container"> \
      <fieldset class="date-range-field date-range-field--wrapped" id="filter-${field}-fields" data-class="daterange" data-field="${field}"> \
        <div> \
          <span class="date-range-field__label">Start:</span> \
          <input type="date" value="" data-field="${field}" \
            aria-label="${title} - Select start date" data-type="start" id="${field}-startdate"> \
        </div> \
        <div> \
          <span class="date-range-field__label">End:</span> \
          <input type="date" value="" data-field="${field}" \
            aria-label="${title} - Select end date" data-type="end" id="${field}-enddate"> \
        </div> \
      </fieldset> \
    </article> \
  </div>',

  SEARCHBAR_GROUP: ' \
  <div class="accordian" data-class="searchbar" data-field="search" data-type="string" \
    role="collapsible" tabindex="0" aria-labelledby="Searchterm Filter" aria-controls="filter-search"> \
    <input class="accordian__input" id="filter-search" name="filter-search" type="checkbox" checked /> \
    <label class="accordian__label" for="filter-search"> \
      <h4>Search</h4> \
    </label> \
    <article class="accordian__container"> \
      <div class="filter-group filter-scrollbar"> \
        <input class="code-text-input" aria-label="Search by term..." type="text" id="searchterm" \
          placeholder="Search..." minlength="3" value="" data-class="searchbar" data-field="search" \
          style="width: calc(100% - 3rem);"> \
      </div> \
    </article> \
  </div>'
};

/**
 * CSEL_FILTER_CLEANSERS
 * @desc Cleans the value of a query by its class
 */
const CSEL_FILTER_CLEANSERS = {
  CHECKBOX: (value) => value.length > 0 ? value.join(',') : null,
  DATEPICKER: (value) => (!isNullOrUndefined(value.start) && !isNullOrUndefined(value.end)) ? `${value.start},${value.end}` : null,
  SEARCHBAR: (value) => !isStringEmpty(value) ? value : null,
  PAGINATION: (value) => value != 1 ? value : null,
  OPTION: (value) => value != 1 ? value : null,
};

/**
 * CSEL_FILTER_APPLICATORS
 * @desc Applies the value of the query to the filter component
 */
const CSEL_FILTER_APPLICATORS = {
  CHECKBOX: (filterGroup, query) => {
    const checkboxes = filterGroup.filter.querySelectorAll('.checkbox-item');
    for (let i = 0; i < checkboxes.length; ++i) {
      let checkbox = checkboxes[i];
      let value = checkbox.getAttribute('data-value');
      if (!isNullOrUndefined(value) && !isNullOrUndefined(query)) {
        let index = query.indexOf(value);
        checkbox.checked = index >= 0;
      } else {
        checkbox.checked = false;
      }
    }
  },

  DATEPICKER: (filterGroup, query) => {
    const dateinputs = filterGroup.filter.querySelectorAll('input[type="date"]');
    for (let i = 0; i < dateinputs.length; ++i) {
      let input = dateinputs[i];
      let value = !isNullOrUndefined(query) ? query?.[type] : null;
      input.value = value;
    }
  },

  SEARCHBAR: (filterGroup, query) => {
    const searchbar = filterGroup.filter.querySelector('#searchterm');
    searchbar.value = !isNullOrUndefined(query) ? query : '';
  },

  OPTION: (filterGroup, query) => {
    for (let i = 0; i < filterGroup.filter.options.length; ++i) {
      const option = filterGroup.filter.options[i];
      option.selected = option.value == query;
      option.dispatchEvent(new CustomEvent('change', { bubbles: true, detail: { filterSet: true } }));
    }
    filterGroup.filter.value = !isNullOrUndefined(query) ? query : 1;
  }
};

/**
 * CSEL_FILTER_GENERATORS
 * @desc Describes how to generate filter groups by their class
 */
const CSEL_FILTER_GENERATORS = {
  // creates a checkbox filter group
  CHECKBOX: (container, data) => {
    if (!data?.options || data.options.length < 1) {
      return;
    }

    let html = interpolateString(CSEL_FILTER_COMPONENTS.CHECKBOX_GROUP, {
      field: data.details.field,
      title: data.details.title,
      datatype: data.details.type,
    });

    let doc = parseHTMLFromString(html);
    let group = container.appendChild(doc.body.children[0]);
    let descendants = group.querySelector('.filter-group');
    for (let i = 0; i < data.options.length; ++i) {
      let option = data.options[i];

      html = interpolateString(CSEL_FILTER_COMPONENTS.CHECKBOX, {
        pk: option.pk,
        field: data.details.field,
        value: option.value,
      });
      doc = parseHTMLFromString(html);
      descendants.appendChild(doc.body.children[0]);
    }

    return group;
  },

  // creates a datepicker filter group
  DATEPICKER: (container, data) => {
    let html = interpolateString(CSEL_FILTER_COMPONENTS.DATEPICKER_GROUP, {
      field: data.details.field,
      title: data.details.title,
      datatype: data.details.type,
    });

    let doc = parseHTMLFromString(html);
    return container.appendChild(doc.body.children[0]);
  },

  // creates a searchbar filter group
  SEARCHBAR: (container, data) => {
    let html = CSEL_FILTER_COMPONENTS.SEARCHBAR_GROUP;
    let doc = parseHTMLFromString(html)
    return container.appendChild(doc.body.children[0]);
  },
}

/**
 * ConceptSelectionService
 * @desc Class that can be used to prompt users to select 1 or more concepts
 *       from a list given by the server, where:
 *          
 *          1. The owner phenotype is published
 *            OR
 *          2. The requesting user has access to the child concepts via permissions
 * 
 */
export class ConceptSelectionService {
  static Views = CSEL_VIEWS;

  constructor(options, data) {
    this.id = generateUUID();
    this.options = mergeObjects(options || { }, CSEL_OPTIONS);
    this.query = { }

    if (this.options.allowMultiple) {
      this.data = data || [ ];
    } else {
      this.data = [ ];
    }
  }


  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getID
   * @desc gets the ID associated with this instance
   * @returns {string} the assoc. UUID
   */
  getID() {
    return this.id;
  }

  /**
   * getQuery
   * @desc gets the current search query params
   * @returns {object} the current query
   */
  getQuery() {
    return this.query;
  }

  /**
   * getSelection
   * @desc gets the currently selected concepts
   * @returns {array} the assoc. data
   */
  getSelection() {
    return this.data;
  }

  /**
   * isOpen
   * @desc reflects whether the dialogue is currently open
   * @returns {boolean} whether the dialogue is open
   */
  isOpen() {
    return !!this.dialogue;
  }

  /**
   * getDialogue
   * @desc get currently active dialogue, if any
   * @returns {object} the dialogue and assoc. elems/methods
   */
  getDialogue() {
    return this.dialogue;
  }

  /**
   * isSelected
   * @param {number} childId 
   * @param {number} childVersion 
   * @returns {boolean} that reflects the selected state of a Concept
   */
  isSelected(childId, childVersion) {
    if (isNullOrUndefined(this.dialogue?.data)) {
      return false;
    }

    return !!this.dialogue.data.find(item => {
      return item.id == childId && item.history_id == childVersion;
    });
  }


  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/  
  /**
   * setSelection
   * @desc sets the currently selected concepts
   * @param {array} data the desired selected objects
   */
  setSelection(data) {
    data = data || [ ];

    if (this.options.allowMultiple) {
      this.data = data;
    }
    return this;
  }


  /*************************************
   *                                   *
   *               Public              *
   *                                   *
   *************************************/
  /**
   * show
   * @desc shows the dialogue
   * @param {enum|int} view the view to open the modal with 
   * @param {object|null} params query parameters to be provided to server to modify Concept results 
   * @returns {promise} a promise that resolves if the selection was confirmed, otherwise rejects
   */
  show(view = CSEL_VIEWS.SEARCH, params) {
    params = params || { };

    // Reject immediately if we currently have a dialogue open
    if (this.dialogue) {
      return Promise.reject();
    }

    return this.#fetchFilterGroups()
      .then(() => new Promise((resolve, reject) => {
        this.#buildDialogue(params);
        this.#renderView(view);

        this.dialogue.element.addEventListener('selectionUpdate', (e) => {
          this.close();
  
          const detail = e.detail;
          const eventType = detail.type;
          const data = detail.data;
          switch (eventType) {
            case CSEL_EVENTS.CONFIRMED: {
              if (this.options.allowMultiple && this.options.maintainSelection) {
                this.data = data;
              }
  
              if (this.options.allowMultiple) {
                resolve(data);
                return;
              }
              resolve(data?.[0]);
            } break;
  
            case CSEL_EVENTS.CANCELLED: {
              reject();
            } break;
  
            default: break;
          }
        });
        
        this.dialogue.show();
      }));
  }
  
  /**
   * close
   * @desc closes the dialogue if active
   */
  close() {
    if (this.dialogue) {
      this.dialogue.close();
    }

    return this;
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  /**
   * cleanQuery
   * @desc collects the data assoc. with each filter after cleaning & applies any forced filters
   * @returns {object} the cleaned query
   */
  #cleanQuery() {
    // clean the query object
    let cleaned = { };
    for (let key in this.query) {
      let value = this.query[key];
      if (this.filters.hasOwnProperty(key)) {
        let filterItem = this.filters[key];
        let uppercase = filterItem.component.toLocaleUpperCase();
        if (CSEL_FILTER_CLEANSERS.hasOwnProperty(uppercase)) {
          value = CSEL_FILTER_CLEANSERS[uppercase](value);
        }
      }

      if (isNullOrUndefined(value)) {
        continue;
      }
      cleaned[key] = value;
    }

    const entity_id = this.options?.entity_id;
    const entity_history_id = this.options?.entity_history_id;
    if (!isNullOrUndefined(entity_id) && !isNullOrUndefined(entity_history_id)) {
      cleaned['parent_id'] = entity_id;
      cleaned['parent_history_id'] = entity_history_id;
    }

    return cleaned;
  }

  /**
   * fetchFilterGroups
   * @returns {object} the spec. for template & metadata filter groups if awaited, otherwise res. a promise
   */
  async #fetchFilterGroups() {
    if (this.filterGroups) {
      return this.filterGroups;
    }

    const response = await fetch(
      `${CSEL_BEHAVIOUR.QUERY_URL}/${this.options?.template}`,
      {
        method: 'GET',
        headers: {
          'X-Target': CSEL_BEHAVIOUR.ENDPOINTS.SPECIFICATION,
          'X-Requested-With': 'XMLHttpRequest',
        }
      }
    );

    if (!response.ok) {
      throw new Error(`An error has occurred: ${response.status}`);
    }

    let res;
    try {
      res = await response.json();
    }
    catch (e) {
      throw new Error(`An error has occurred: ${e}`); 
    }

    if (this.options?.ignoreFilters) {
      Object.keys(res).forEach((key, index) => {
        res[key] = res[key].filter(item => !this.options.ignoreFilters.includes(item?.details?.field));
      });
    }

    this.filterGroups = res;
    return this.filterGroups;
  }

  /**
   * tryGetSearchResults
   * @desc GET request to search endpoint for results that relate to options & filter params
   * @param {string} cacheState which cache state to use
   * @returns {array} the search results matching our current query 
   */
  async #tryGetSearchResults(cacheState = 'force-cache') {
    if (!this.options?.useCachedResults) {
      cacheState = 'reload';
    }

    // build params
    const query = this.#cleanQuery();
    const params = new URLSearchParams(query);
    const request = {
      method: 'GET',
      headers: {
        'X-Target': CSEL_BEHAVIOUR.ENDPOINTS.RESULTS,
        'X-Requested-With': 'XMLHttpRequest',
      }
    };

    // toggle filter reset button visibility
    this.#toggleResetButton(query);

    // query results
    if (cacheState) {
      request.cache = cacheState;
    }

    const response = await fetch(
      `${CSEL_BEHAVIOUR.QUERY_URL}/${this.options?.template}/?` + params,
      request
    );

    if (!response.ok) {
      throw new Error(`An error has occurred: ${response.status}`);
    }

    if (cacheState !== 'reload') {
      const date = response.headers.get('date');
      const delta = date ? new Date(date).getTime() : 0;
      if (delta < Date.now() - CSEL_BEHAVIOUR.CACHE_TIME) {
        return this.#tryGetSearchResults('reload');
      }
    }

    let res;
    try {
      res = await response.json();
    }
    catch (e) {
      throw new Error(`An error has occurred: ${e}`); 
    }

    return res;
  }

  /**
   * getFilterSafeChildren
   * @desc applies filters to a child object if present within the query, e.g. coding system(s)
   * @param {list|null} children the list of children associated with a child object
   * @returns {list|null} the list of filtered children (or null if no children present)
   */
  #getFilterSafeChildren(children) {
    if (isNullOrUndefined(children) || children.length < 1) {
      return;
    }

    const childFilters = this.options?.childFilters;
    if (isNullOrUndefined(childFilters)) {
      return children;
    }

    let output = [ ];
    for (let i = 0; i < children.length; ++i) {
      let child = children[i];
      let passed = true;
      for (let j = 0; j < childFilters.length; ++j) {
        let filter = childFilters[j];
        let query = this.query?.[filter];
        if (isNullOrUndefined(child?.[filter])) {
          continue;
        }

        if (!isNullOrUndefined(query)) {
          if (typeof query === 'array' && !query.includes(child[filter])) {
            passed = false;
            continue;
          } else if (typeof child[filter] === typeof query && child[filter] != query) {
            passed = false;
            continue;
          }
        }
      }

      if (passed) {
        output.push(child);
      }
    }

    return output;
  }

  /**
   * resetPage
   * @desc Force reset page on filter mutation
   */
  #resetPage() {
    if (isNullOrUndefined(this.query.page)) {
      return;
    }
    this.query.page = 1;
  }


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * buildDialogue
   * @desc renders the top-level modal according to the options given
   * @param {object} params the given query params
   * @returns {object} the dialogue object as assigned to this.dialogue
   */
  #buildDialogue(params) {
    // create dialogue
    const currentHeight = window.scrollY;
    let html = interpolateString(CSEL_INTERFACE.DIALOGUE, {
      id: this.id,
      promptTitle: this.options?.promptTitle,
      promptSize: this.options?.promptSize,
      hidden: 'false',
    });
  
    let doc = parseHTMLFromString(html);
    let modal = document.body.appendChild(doc.body.children[0]);
    
    // create footer
    let footer = createElement('div', {
      id: 'target-modal-footer',
      class: 'target-modal__footer',
    });
  
    const container = modal.querySelector('.target-modal__container');
    footer = container.appendChild(footer);
    
    // create buttons
    const buttons = { };
    let confirmBtn = parseHTMLFromString(CSEL_BUTTONS.CONFIRM);
    confirmBtn = footer.appendChild(confirmBtn.body.children[0]);
    confirmBtn.innerText = this.options.promptConfirm;

    let cancelBtn = parseHTMLFromString(CSEL_BUTTONS.CANCEL);
    cancelBtn = footer.appendChild(cancelBtn.body.children[0]);
    cancelBtn.innerText = this.options.promptCancel;

    buttons['confirm'] = confirmBtn;
    buttons['cancel'] = cancelBtn;

    // initiate main event handling
    buttons?.confirm.addEventListener('click', this.#handleConfirm.bind(this));
    buttons?.cancel.addEventListener('click', this.#handleCancel.bind(this));

    // create content handler
    const body = container.querySelector('#target-modal-content');
    if (this.options?.allowMultiple) {
      body.classList.add('target-modal__body--no-pad');
      body.classList.add('target-modal__body--constrained');
    }

    let contentContainer = body;
    if (this.options.allowMultiple) {
      html = CSEL_INTERFACE.TAB_VIEW;
      doc = parseHTMLFromString(html);
      contentContainer = body.appendChild(doc.body.children[0]);
      
      const tabs = contentContainer.querySelectorAll('button.tab-view__tab');
      for (let i = 0; i < tabs.length; ++i) {
        tabs[i].addEventListener('click', this.#changeTabView.bind(this));
      }

      contentContainer = contentContainer.querySelector('#tab-content');
    }

    // build dialogue
    this.dialogue = {
      // data
      data: this.options?.maintainSelection ? this.data : [],
      params: params,
      view: CSEL_VIEWS.SEARCH,

      // dialogue elements
      element: modal,
      buttons: buttons,
      content: contentContainer,

      // dialogue methods
      show: () => {
        createElement('a', { href: `#${this.id}` }).click();
        window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
    
        // inform screen readers of alert
        modal.setAttribute('aria-hidden', false);
        modal.setAttribute('role', 'alert');
        modal.setAttribute('aria-live', true);
        
        // stop body scroll
        document.body.classList.add('modal-open');
      },
      close: () => {
        this.dialogue = null;

        document.body.classList.remove('modal-open');
        modal.remove();
        history.replaceState({ }, document.title, '#');
        window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
      },
    };

    return this.dialogue;
  }

  /**
   * renderView
   * @desc renders the given view
   * @param {enum|int} view the view to render within the active dialogue
   */
  #renderView(view) {
    if (!this.isOpen()) {
      return;
    }
    
    if (!this.options.allowMultiple && view == CSEL_VIEWS.SELECTION) {
      view = CSEL_VIEWS.SEARCH;
    }
    this.dialogue.view = view;

    const content = this.dialogue?.content;
    if (!isNullOrUndefined(content)) {
      content.innerHTML = '';
    }

    if (this.options.allowMultiple) {
      this.#pushActiveTab(view);
    }

    switch (view) {
      case CSEL_VIEWS.SEARCH: {
        this.#renderSearchView();
      } break;

      case CSEL_VIEWS.SELECTION: {
        this.#renderSelectionView();
      } break;

      default: break;
    }
  }

  /**
   * renderSearchView
   * @desc renders the search view where users can select concepts to import
   */
  #renderSearchView() {
    // Draw page
    let html = CSEL_INTERFACE.SEARCH_VIEW;
    let doc = parseHTMLFromString(html);
    let page = this.dialogue.content.appendChild(doc.body.children[0]);
    this.dialogue.page = page;
    
    // Draw content
    this.filters = { };
    if (!this.options?.maintainFilters) {
      this.query = { };
    }

    if (this.options?.forceFilters) {
      this.query = mergeObjects(this.query, this.options.forceFilters);
    }
    
    this.#paintSearchFilters();
    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
  }

  /**
   * renderSelectionView
   * @desc renders the selection view where users can manage their currently selected concepts
   */
  #renderSelectionView() {
    // Draw page
    let html = interpolateString(CSEL_INTERFACE.SELECTION_VIEW, {
      noneSelectedMessage: this.options?.noneSelectedMessage,
    });
  
    let doc = parseHTMLFromString(html);
    let page = this.dialogue.content.appendChild(doc.body.children[0]);
    this.dialogue.page = page;

    // Draw content
    this.#paintSelectionList();
  }

  /**
   * pushActiveTab
   * @desc updates the tab view objects when allowMultiple flag is true
   * @param {int|enum} view an enum of CSEL_VIEWS
   */
  #pushActiveTab(view) {
    let tabs = this.dialogue.element.querySelectorAll('button.tab-view__tab');
    for (let i = 0; i < tabs.length; ++i) {
      let tab = tabs[i];
      let relative = tab.getAttribute('id');
      if (!CSEL_VIEWS.hasOwnProperty(relative)) {
        continue;
      }

      relative = CSEL_VIEWS[relative];
      if (relative == view) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    }
  }

  /**
   * paintSelectionList
   * @desc renders the selected items
   */
  #paintSelectionList() {
    const page = this.dialogue.page;
    const selectedData = this.dialogue?.data;
    if (!this.dialogue?.view == CSEL_VIEWS.SELECTION || isNullOrUndefined(page)) {
      return;
    }

    const content = page.querySelector('#item-list');
    const noneAvailable = page.querySelector('#no-items-selected');
    if (isNullOrUndefined(content) || isNullOrUndefined(noneAvailable)) {
      return;
    }

    const hasSelectedItems = !isNullOrUndefined(selectedData) && selectedData.length > 0;

    // Display none available if no items selected
    if (!hasSelectedItems) {
      content.classList.add('hide');
      noneAvailable.classList.add('show');
      return;
    }

    // Render selected items if available
    for (let i = 0; i < selectedData.length; ++i) {
      let selected = selectedData?.[i];
      let html = interpolateString(CSEL_INTERFACE.CHILD_SELECTOR, {
        'id': selected.id,
        'history_id': selected.history_id,
        'field': selected.type,
        'title': selected.name,
        'coding_system': selected.coding_system_name,
        'prefix': selected.prefix,
        'checked': true,
        'isSelector': false,
        'index': i,
      });

      let doc = parseHTMLFromString(html);
      let checkbox = content.appendChild(doc.body.children[0]);
      checkbox.addEventListener('change', this.#handleSelectedItem.bind(this));
    }
  }

  /**
   * paintSearchFilters
   * @desc renders the filters per the spec
   */
  #paintSearchFilters() {
    const filterContainer = this.dialogue.page.querySelector('#search-filters');
    if (isNullOrUndefined(filterContainer)) {
      return;
    }

    // Paint searchbar
    const searchbar = CSEL_FILTER_GENERATORS.SEARCHBAR(filterContainer);
    this.filters['search'] = {
      name: 'search',
      filter: searchbar,
      component: 'searchbar',
      datatype: 'string',
    };
    this.#handleClientInteraction(this.filters['search']);

    // Paint order by filter
    const orderFilter = this.dialogue.page.querySelector('#order-by-filter');
    createDropdownSelectionElement(orderFilter);
    this.filters['order_by'] = {
      name: 'order_by',
      filter: orderFilter,
      component: 'option',
      datatype: 'int',
    };
    this.#handleClientInteraction(this.filters['order_by']);

    // Paint metadata -> template filterable fields
    const { metadata, template } = this.filterGroups;
    for (let i = 0; i < metadata.length; ++i) {
      const group = metadata[i];
      const handler = CSEL_FILTER_GENERATORS[group?.details?.component.toLocaleUpperCase()];
      if (isNullOrUndefined(handler)) {
        continue;
      }

      const filterComponent = handler(filterContainer, group);
      if (isNullOrUndefined(filterComponent)) {
        continue;
      }

      this.filters[group?.details?.field] = {
        name: group?.details?.field,
        fieldtype: 'metadata',
        filter: filterComponent,
        component: group?.details?.component,
        datatype: group?.details?.type,
      };
      this.#handleClientInteraction(this.filters[group?.details?.field]);
    }

    for (let i = 0; i < template.length; ++i) {
      const group = template[i];
      const handler = CSEL_FILTER_GENERATORS[group?.details?.component.toLocaleUpperCase()];
      if (isNullOrUndefined(handler)) {
        continue;
      }

      const filterComponent = handler(filterContainer, group);
      if (isNullOrUndefined(filterComponent)) {
        continue;
      }

      this.filters[group?.details?.field] = {
        name: group?.details?.field,
        fieldtype: 'template',
        filter: filterComponent,
        component: group?.details?.component,
        datatype: group?.details?.type,
      };
      this.#handleClientInteraction(this.filters[group?.details?.field]);
    }

    const resetButton = this.dialogue.page.querySelector('#reset-filter-btn');
    if (!isNullOrUndefined(resetButton)) {
      resetButton.addEventListener('click', this.#handleFilterReset.bind(this));
    }
  }

  /**
   * paintSearchPagination
   * @desc paints the pagination controller
   * @param {array} results the results as returned from the search api
   */
  #paintSearchPagination(response) {
    const page = this.dialogue.page;
    if (!this.dialogue?.view == CSEL_VIEWS.SEARCH || isNullOrUndefined(page)) {
      return;
    }

    const pageContainer = page.querySelector('#search-pagination-area');
    if (isNullOrUndefined(pageContainer)) {
      return;
    }
    pageContainer.innerHTML = '';

    // paint new pagination
    let html = interpolateString(CSEL_INTERFACE.SEARCH_PAGINATION, {
      'page': response?.details?.page,
      'page_total': response?.details?.total,
      'prev_disabled': !response?.details?.has_previous,
      'next_disabled': !response?.details?.has_next,
    });

    let doc = parseHTMLFromString(html);
    let pagination = pageContainer.appendChild(doc.body.children[0]);

    this.filters['page'] = {
      name: 'page',
      filter: pagination,
      component: 'pagination',
      datatype: 'int',
    };
    this.#handleClientInteraction(this.filters['page']);

    // update page result count
    const textCounter = page.querySelector('#search-response-header > p');
    if (textCounter) {
      textCounter.innerText = `${response?.details?.start_index}-${response?.details?.end_index} of over ${response?.details?.max_results.toLocaleString()}`;
    }    
  }

  /**
   * paintSearchResults
   * @desc makes a request to the endpoint to get search results and paints them to the screen
   * @param {array} results the results as returned from the search api
   */
  #paintSearchResults(response) {
    const page = this.dialogue.page;
    if (!this.dialogue?.view == CSEL_VIEWS.SEARCH || isNullOrUndefined(page)) {
      return;
    }

    const resultContainer = page.querySelector('#search-response-content');
    if (isNullOrUndefined(resultContainer)) {
      return;
    }

    // first clear prev. results
    resultContainer.innerHTML = '';

    // then render cards, apply selection to concepts if found
    const results = response?.results || [ ];
    for (let i = 0; i < results.length; ++i) {
      let result = results[i];
      let children = this.#getFilterSafeChildren(result?.children);
      if (isNullOrUndefined(children) || children.length < 1) {
        continue;
      }

      let html = interpolateString(CSEL_INTERFACE.RESULT_CARD, {
        'id': result?.id,
        'name': result?.name,
        'history_id': result?.history_id,
        'author': result?.author || '',
        'tags': '',
      });
      
      let doc = parseHTMLFromString(html);
      let card = resultContainer.appendChild(doc.body.children[0]);
      let datagroup = card.querySelector('#datagroup');

      let childContents = '';
      for (let j = 0; j < children.length; ++j) {
        let child = children[j];
        childContents += interpolateString(CSEL_INTERFACE.CHILD_SELECTOR, {
          'id': child.id,
          'history_id': child.history_id,
          'field': child.type,
          'title': `${child.prefix}${child.id}/${child.history_id} - ${child.name}`,
          'checked': this.isSelected(child.id, child.history_id),
          'coding_system': child.coding_system_name,
          'prefix': child.prefix,
          'isSelector': true,
          'index': -1,
        });
      }

      html = interpolateString(CSEL_INTERFACE.CARD_ACCORDIAN, {
        id: result?.id,
        title: `Available Concepts (${children.length})`,
        content: childContents,
      });
      doc = parseHTMLFromString(html);

      let accordian = datagroup.appendChild(doc.body.children[0]);
      let checkboxes = accordian.querySelectorAll('#child-selector > input[type="checkbox"]');
      for (let j = 0; j < checkboxes.length; j++) {
        let checkbox = checkboxes[j];
        checkbox.addEventListener('change', this.#handleChildSelection.bind(this));
      }
    }

    // paint pagination
    this.#paintSearchPagination(response);
  }

  /**
   * toggleResetButton
   * @desc toggles the reset button's visibility, dependent on whether
   *       filters are currently applied
   * @param {object} query the filters that are being currently applied
   */
  #toggleResetButton(query) {
    const resetButton = this.dialogue.page.querySelector('#reset-filter-btn');
    if (!isNullOrUndefined(resetButton)) {
      const trueQuery = Object.keys(query)
                              .filter(key => isNullOrUndefined(this.options?.forceFilters) || !this.options?.forceFilters.hasOwnProperty(key))
                              .reduce((obj, key) => {
                                obj[key] = query[key];
                                return obj;
                              }, {});

      const hasFilters = Object.values(trueQuery);
      if (hasFilters.length > 0) {
        resetButton.classList.add('show');
      } else {
        resetButton.classList.remove('show');
      }
    }
  }

  /**
   * applyFilterStates
   * @desc applies the filter's state to the filter's component
   * @param {object} filterGroup the filter group and assoc. data
   */
  #applyFilterStates(filterGroup) {
    const componentType = filterGroup?.component;
    if (isNullOrUndefined(componentType)) {
      return;
    }

    const applicator = CSEL_FILTER_APPLICATORS?.[componentType.toLocaleUpperCase()];
    if (isNullOrUndefined(applicator)) {
      return;
    }

    try {
      applicator(filterGroup, this.query?.[filterGroup.name]);
    }
    catch (e) {
      console.warn(e);
    }
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleClientInteraction
   * @desc initiates event handling for filters
   * @param {object} filterGroup the filter group as described by the spec 
   */
  #handleClientInteraction(filterGroup) {
    this.#applyFilterStates(filterGroup);

    switch (filterGroup.component) {
      case 'checkbox': {
        const checkboxes = filterGroup.filter.querySelectorAll('.checkbox-item');
        for (let i = 0; i < checkboxes.length; ++i) {
          let checkbox = checkboxes[i];
          checkbox.addEventListener('change', this.#handleCheckboxUpdate.bind(this));
        }
      } break;

      case 'datepicker': {
        const dateinputs = filterGroup.filter.querySelectorAll('input[type="date"]');
        for (let i = 0; i < dateinputs.length; ++i) {
          let input = dateinputs[i];
          input.addEventListener('change', this.#handleDateUpdate.bind(this));
        }
      } break;

      case 'searchbar': {
        const searchbar = filterGroup.filter.querySelector('#searchterm');
        searchbar.addEventListener('keyup', this.#handleSearchbarUpdate.bind(this));
      } break;

      case 'pagination': {
        const value = this.query?.[filterGroup.name];
        if (!isNullOrUndefined(value)) {
          filterGroup.filter.setAttribute('data-value', value);
        }

        const previous = filterGroup.filter.querySelector('a[data-value="previous"]');
        previous.addEventListener('click', this.#handlePaginationUpdate.bind(this));

        const next = filterGroup.filter.querySelector('a[data-value="next"]');
        next.addEventListener('click', this.#handlePaginationUpdate.bind(this));
      } break;

      case 'option': {
        filterGroup.filter.addEventListener('change', this.#handleOptionUpdate.bind(this));
      } break;

      default: break;
    }
  }

  /**
   * handleSelectedItem
   * @desc handles the change event for selected items within selection view
   * @param {event} e the assoc. event
   */
  #handleSelectedItem(e) {
    const target = e.target;
    const targetId = parseInt(target.getAttribute('data-id'));
    const targetHistoryId = parseInt(target.getAttribute('data-history'));
    const index = this.dialogue.data.findIndex(x => x?.id == targetId && x?.history_id == targetHistoryId);
    if (isNullOrUndefined(index)) {
      return;
    }
    
    this.dialogue.data.splice(index, 1);
    target.parentNode.remove();

    const page = this.dialogue.page;
    if (isNullOrUndefined(page)) {
      return;
    }

    const content = page.querySelector('#item-list');
    const noneAvailable = page.querySelector('#no-items-selected');
    if (isNullOrUndefined(content) || isNullOrUndefined(noneAvailable)) {
      return;
    }

    const hasSelectedItems = !isNullOrUndefined(this.dialogue.data) && this.dialogue.data.length > 0;
    if (!hasSelectedItems) {
      content.classList.add('hide');
      noneAvailable.classList.add('show');
    } else {
      content.classList.remove('hide');
      noneAvailable.classList.remove('show');
    }
  }

  /**
   * handleChildSelection
   * @desc handles the change event for child selector components
   * @param {event} e the assoc. event
   */
  #handleChildSelection(e) {
    const target = e.target;
    const field = target.getAttribute('data-field');
    const name = target.getAttribute('data-name');
    const prefix = target.getAttribute('data-prefix');
    const codingSystem = target.getAttribute('data-coding');

    let childId = target.getAttribute('data-id');
    let childVersion = target.getAttribute('data-history');
    if (isNullOrUndefined(field) || isNullOrUndefined(childId) || isNullOrUndefined(childVersion)) {
      return;
    }

    childId = parseInt(childId);
    childVersion = parseInt(childVersion);

    if (target.checked) {
      if (this.isSelected(childId, childVersion)) {
        return;
      }

      const packet = {
        id: childId,
        name: name,
        type: field,
        history_id: childVersion,
        prefix: prefix,
        coding_system_name: codingSystem,
      };
      
      if (this.options.allowMultiple) {
        this.dialogue.data.push(packet);
        return;
      }

      const checkboxes = this.dialogue.page.querySelectorAll('#child-selector > input[type="checkbox"]');
      for (let i = 0; i < checkboxes.length; ++i) {
        let checkbox = checkboxes[i];
        if (checkbox.checked && checkbox.getAttribute('id') != target.getAttribute('id')) {
          checkbox.checked = false;
        }
      }
      this.dialogue.data[0] = packet;
      return;
    }
    
    if (!this.isSelected(childId, childVersion)) {
      return;
    }
    
    const index = this.dialogue.data.findIndex(item => item.id == childId && item.history_id == childVersion);
    this.dialogue.data.splice(index, 1);
  }

  /**
   * handleCheckboxUpdate
   * @desc handles the change event when a checkbox component is modified
   * @param {event} e the assoc. event
   */
  #handleCheckboxUpdate(e) {
    const target = e.target;
    const field = target.getAttribute('data-field');
    const value = target.getAttribute('data-value');
    if (isNullOrUndefined(field) || isNullOrUndefined(value)) {
      return;
    }

    if (!this.query.hasOwnProperty(field)) {
      this.query[field] = [];
    }

    const index = this.query[field].indexOf(value);
    if (target.checked) {
      if (index >= 0) {
        return;
      }

      this.query[field].push(value);
      this.#resetPage();
      this.#tryGetSearchResults()
        .then((results) => this.#paintSearchResults(results))
        .catch(console.warn);

      return;
    }

    if (index < 0) {
      return;
    }

    this.query[field].splice(index, 1);
    this.#resetPage();
    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
    
    return;
  }

  /**
   * handleDateUpdate
   * @desc handles the change event when a input[type=date] component is modified
   * @param {event} e the assoc. event
   */
  #handleDateUpdate(e) {
    const target = e.target;
    const field = target.getAttribute('data-field');
    const type = target.getAttribute('data-type');
    if (isNullOrUndefined(field) || isNullOrUndefined(type)) {
      return;
    }

    if (!target.checkValidity()) {
      return;
    }

    if (!this.query.hasOwnProperty(field)) {
      this.query[field] = { start: null, end: null };
    }
    
    let datetime = moment(target.value, CSEL_BEHAVIOUR.ACCEPTABLE_DATE_FORMAT);
    this.query[field][type] = datetime.isValid() ? datetime.format(CSEL_BEHAVIOUR.DATE_FORMAT) : null;

    let dates = Object.values(this.query[field])
      .filter(x => !isNullOrUndefined(x) && moment(x, CSEL_BEHAVIOUR.DATE_FORMAT).isValid())
      .sort((a, b) => moment(a, CSEL_BEHAVIOUR.DATE_FORMAT).diff(moment(b, CSEL_BEHAVIOUR.DATE_FORMAT)));
  
    if (dates.length > 1) {
      let [ startDate, endDate ] = dates;
      this.query[field].start = startDate;
      this.query[field].end = endDate;
      this.#resetPage();
    }

    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
  }

  /**
   * handlePaginationUpdate
   * @desc click event that handles pagination events
   * @param {event} e the assoc. event
   */
  #handlePaginationUpdate(e) {
    e.preventDefault();

    const target = e.target;
    const field = target.getAttribute('data-field');
    if (isNullOrUndefined(field)) {
      return;
    }
    
    let value = target.getAttribute('data-value');
    if (isNullOrUndefined(value)) {
      return;
    }

    if (value === CSEL_BEHAVIOUR.PAGINATION.NEXT || value === CSEL_BEHAVIOUR.PAGINATION.PREVIOUS) {
      const offset = value === CSEL_BEHAVIOUR.PAGINATION.NEXT ? 1 : -1;
      const current = this.query.hasOwnProperty(field) ? this.query[field] : 1;
      value = current + offset;
    }

    value = parseInt(value);
    if (isNaN(value)) {
      return;
    }

    if (this.options?.scrollOnResultChange) {
      const container = this.dialogue?.page.querySelector('#search-response-content');
      if (container) {
        container.scroll({ top: 0, behaviour: 'smooth' });
      }
    }

    this.query[field] = value;
    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
  }

  /**
   * handleSearchbarUpdate
   * @desc handles the key up event when a searchbar is modified
   * @param {event} e the assoc. event
   */
  #handleSearchbarUpdate(e) {
    const code = e.keyIdentifier || e.which || e.keyCode;
    if (code != CSEL_BEHAVIOUR.KEY_CODES.ENTER) {
      return;
    }

    const target = e.target;
    const field = target.getAttribute('data-field');
    const value = target.value;
    if (isNullOrUndefined(field) || isNullOrUndefined(value)) {
      return;
    }

    const current = this.query.hasOwnProperty(field) ? this.query[field] : '';
    if (current === value) {
      return;
    }

    this.query[field] = value;
    this.#resetPage();
    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
  }

  /**
   * handleOptionUpdate
   * @desc handles dropdown event fired by option filters e.g. order_by
   * @param {event} e the assoc. event
   */
  #handleOptionUpdate(e) {
    const field = e.target.getAttribute('data-field');
    if (isNullOrUndefined(field) || isStringEmpty(field)) {
      return;
    }

    if (!isNullOrUndefined(e.detail) && 'filterSet' in e.detail) {
      return;
    }

    const filterItem = this.filters[field];
    this.query[field] = filterItem.filter.value;
    this.#resetPage();
    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
  }

  /**
   * handleCancel
   * @desc handles the cancel/exit btn
   * @param {event} e the assoc. event
   */
  #handleCancel(e) {
    if (!this.isOpen()) {
      return;
    }

    const event = new CustomEvent(
      'selectionUpdate',
      {
        detail: {
          type: CSEL_EVENTS.CANCELLED,
        }
      }
    );
    this.dialogue?.element.dispatchEvent(event);
  }

  /**
   * handleConfirm
   * @desc handles the confirmation btn
   * @param {event} e the assoc. event
   */
  #handleConfirm(e) {
    if (!this.isOpen()) {
      return;
    }

    const data = this.dialogue?.data;
    const event = new CustomEvent(
      'selectionUpdate',
      {
        detail: {
          data: data,
          type: CSEL_EVENTS.CONFIRMED,
        }
      }
    );
    this.dialogue?.element.dispatchEvent(event);
  }

  /**
   * changeTabView
   * @desc handles the tab buttons
   * @param {event} e the assoc. event
   */
  #changeTabView(e) {
    const target = e.target;
    const desired = target.getAttribute('id');
    if (target.classList.contains('active')) {
      return;
    }

    if (!desired || !CSEL_VIEWS.hasOwnProperty(desired)) {
      return;
    }

    this.#renderView(CSEL_VIEWS[desired]);
  }

  /**
   * handleFilterReset
   * @desc handles the reset of filters, if applied
   * @params {event} e the assoc. event
   */
  #handleFilterReset(e) {
    this.query = { };

    if (this.options?.forceFilters) {
      this.query = mergeObjects(this.query, this.options.forceFilters);
    }
    
    for (const [name, filterGroup] of Object.entries(this.filters)) {
      this.#applyFilterStates(filterGroup);
    }

    this.#tryGetSearchResults()
      .then((results) => this.#paintSearchResults(results))
      .catch(console.warn);
  }
}
