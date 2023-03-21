/**
 * FILTER_SCROLL_TOP_ON_PAGE_CHANGE
 * @desc Flag to determine whether we scroll to the top of the page when pagination
 *       buttons are interacted with
 */
const FILTER_SCROLL_TOP_ON_PAGE_CHANGE = true;

/**
 * FILTER_DATEPICKER_FORMAT
 * @desc Defines format behaviour of datetime objects for datepicker-related filters
 */
const FILTER_DATEPICKER_FORMAT = 'YYYY-MM-DD';

/**
 * FILTER_KEYCODES
 * @desc Describes keycodes for filter related events
 * 
 */
const FILTER_KEYCODES = {
  ENTER: 13,
};

/**
 * FILTER_PAGINATION
 * @desc Describes non-numerical data-value targets for pagination buttons,
 *       e.g. previous and/or next buttons, used as default variables that
 *       can be updated in the future to reflect the pagination component
 * 
 */
const FILTER_PAGINATION = {
  NEXT: 'next',
  PREVIOUS: 'previous',
}

/**
 * FILTER_RESPONSE_CONTENT_IDS
 * @desc Defines the IDs of nodes that are swapped after a meaningful response
 * 
 */
const FILTER_RESPONSE_CONTENT_IDS = {
  HEADER: '#entity-search-response-header',
  RESULTS: '#entity-search-response-content',
  PAGINATION: '#entity-pagination-response',
}

/**
  * FILTER_PARSERS
  * @desc Hashmap of methods to parse query param values by filter type
  * 
  */
const FILTER_PARSERS = {
  // No parsing needed, able to treat search param as a string
  searchbar: (values) => values,
  
  // Parses pagination value as an int or returns default of 1
  pagination: (values) => parseInt(values) || 1,
  
  // Parses checkbox filter items as a number, if unable to parse as num, filters from list
  checkbox: (values) => values.split(',')
                              .filter(n => !isNaN(parseInt(n))),
  
  // Parses datetime filters as datetime objects, takes only the first two valid values
  datepicker: (values) => values.split(',')
                                .map(date => moment(date))
                                .filter(date => date.isValid())
                                .slice(0, 2)
                                .sort((a, b) => -a.diff(b)),
  
  // Parses options e.g. page_size, order_by
  option: (values) => parseInt(values) || 1,
};

/**
 * FILTER_CLEANSERS
 * @desc Cleans the value of a query by its filterClass
 * 
 */
const FILTER_CLEANSERS = {
  checkbox: (value) => value.length > 0 ? value.join(',') : null,
  datepicker: (value) => value.length > 1 ? value.join(',') : null,
  searchbar: (value) => !isStringEmpty(value) ? value : null,
  pagination: (value) => value != 1 ? value : null,
  option: (value) => value != 1 ? value : null,
}

/**
  * FILTER_APPLICATORS
  * @desc Hashmap of applicator methods that update the DOM to reflect query parameters
  *       by filter type
  * 
  */
const FILTER_APPLICATORS = {
  // Applies 'checked' attribute to the filters that match the query params
  checkbox: (filterItem, values) => {
    const inputs = filterItem.filter.querySelectorAll('input[data-class="checkbox"]');
    for (let i = 0; i < inputs.length; ++i) {
      const input = inputs[i];
      const value = input.getAttribute('data-value');
      input.checked = values.indexOf(value) >= 0;
    }
  },
  
  // Applies the date/date range to the datepicker according to query params
  datepicker: (filterItem, values) => {
    if (values.length === 0) {
      return;
    }

    if (!filterItem.hasOwnProperty('datepicker')) {
      return;
    }

    const datepicker = filterItem.datepicker;
    if (values.length > 1) {
      const [start, end] = values.map(date => date.format(FILTER_DATEPICKER_FORMAT));
      datepicker.setDateRange(end, start, true);
      return;
    }
    
    const start = values[0].format(FILTER_DATEPICKER_FORMAT)
    const end = moment().format(FILTER_DATEPICKER_FORMAT);
    datepicker.setDateRange(start, end, true);
  },

  // Applies the query params to the searchbar(s)
  searchbar: (filterItem, values) => {
    const input = filterItem.filter.querySelector('input[data-class="searchbar"]');
    input.value = values;
  },

  // Option e.g. page_size, order_by
  option: (filterItem, values) => {
    const input = filterItem.filter;
    for (let i = 0; i < input.options.length; ++i) {
      const option = input.options[i];
      option.selected = option.value == values
      option.dispatchEvent(new CustomEvent('change', { bubbles: true, detail: { filterSet: true } }));
    }
  },
};

/**
  * FilterService
  * @desc A class that can be used to control filters for dynamic search
  *       pages with dynamic filters, search and pagination.
  *       
  */
class FilterService {
  constructor() {
    this.query = { };
    this.filters = { };

    this.#collectFilters();
    this.#setUpFilters();
    this.#fetchURLParameters();
    this.#handleHistoryUpdate();
  }

  // Public getter methods
  getAllFilters() {
    return this.filters;
  }

  getCurrentParameters() {
    return this.query;
  }

  // Private request methods
  #cleanQuery() {
    const cleaned = { }
    for (let key in this.query) {
      if (!this.query.hasOwnProperty(key)) {
        continue;
      }

      let value = this.query[key];
      if (!this.filters.hasOwnProperty(key)) {
        continue;
      }

      const filterItem = this.filters[key];
      if (FILTER_CLEANSERS.hasOwnProperty(filterItem.filterClass)) {
        const cleanser = FILTER_CLEANSERS[filterItem.filterClass];
        value = cleanser(value);
      }

      if (isNullOrUndefined(value)) {
        continue;
      }
      
      cleaned[key] = value;
    }

    return cleaned;
  }

  #renderResponse(html) {
    const parser = new DOMParser();
    const response = parser.parseFromString(html, 'text/html');

    const resultsHeader = response.querySelector(FILTER_RESPONSE_CONTENT_IDS.HEADER);
    if (!isNullOrUndefined(resultsHeader)) {
      const header = document.querySelector(FILTER_RESPONSE_CONTENT_IDS.HEADER);
      if (!isNullOrUndefined(header)) {
        header.replaceWith(resultsHeader);
      }
    }

    const resultsContainer = response.querySelector(FILTER_RESPONSE_CONTENT_IDS.RESULTS);
    if (!isNullOrUndefined(resultsContainer)) {
      const results = document.querySelector(FILTER_RESPONSE_CONTENT_IDS.RESULTS);
      if (!isNullOrUndefined(results)) {
        results.replaceWith(resultsContainer);
      }
    }

    const paginationContainer = response.querySelector(FILTER_RESPONSE_CONTENT_IDS.PAGINATION);
    if (!isNullOrUndefined(paginationContainer)) {
      const pagination = document.querySelector(FILTER_RESPONSE_CONTENT_IDS.PAGINATION);
      if (!isNullOrUndefined(pagination)) {
        pagination.replaceWith(paginationContainer);

        const filter = document.querySelector('[data-class="pagination"]');
        this.filters['page'].filter = filter;
      }
    }
  }

  #applyURLParameters(query) {
    delete query.search_filtered;

    const parameters = new URLSearchParams(query);
    const url = `${getCurrentURL()}?` + parameters
    window.history.pushState({}, document.title, url);
  }

  #postQuery() {
    let query = this.#cleanQuery();
    query = mergeObjects(query, {'search_filtered': true});

    const parameters = new URLSearchParams(query);
    fetch(
      `${getCurrentURL()}?` + parameters,
      {
        'X-Requested-With': 'XMLHttpRequest',
      }
    )
      .then(response => response.text())
      .then(html => this.#renderResponse(html))
      .then(() => this.#setUpPagination('page'))
      .then(() => this.#applyURLParameters(query))
      .catch(error => console.error(error));
  }

  // Private initialisation methods
  #collectFilters() {
    const filters = document.querySelectorAll('[data-controller="filter"]');
    for (let i = 0; i < filters.length; ++i) {
      const filter = filters[i];
      const filterClass = filter.getAttribute('data-class');
      const filterField = filter.getAttribute('data-field');
      this.filters[filterField] = {
        filter: filter,
        filterClass: filterClass,
      };
    }
  }

  #fetchURLParameters(location) {
    const params = new URL(location == undefined ? window.location.href : location);
    params.searchParams.forEach((value, key) => {
      if (key in this.filters) {
        const filterItem = this.filters[key];
        const parser = FILTER_PARSERS[filterItem.filterClass];
        value = parser(value);

        if (FILTER_APPLICATORS.hasOwnProperty(filterItem.filterClass)) {
          const applicator = FILTER_APPLICATORS[filterItem.filterClass];
          applicator(filterItem, value);
        }
        this.query[key] = value;
      }
    });
  }

  #setUpFilters() {
    for (let key in this.filters) {
      if (!this.filters.hasOwnProperty(key)) {
        continue;
      }

      const filterItem = this.filters[key];
      switch (filterItem.filterClass) {
        case 'datepicker': {
          this.#setUpDatepicker(key);
        } break;

        case 'checkbox': {
          this.#setUpCheckbox(key);
        } break;

        case 'searchbar': {
          this.#setUpSearchbar(key);
        } break;

        case 'pagination': {
          this.#setUpPagination(key);
        } break;

        case 'option': {
          this.#setUpOptions(key);
        } break;
      }
    }
  }

  // Private interface setup methods
  #setUpDatepicker(field) {
    const input = this.filters[field].filter.querySelector('.date-range-picker');
    const datepicker = new Lightpick({
      field: input,
      singleDate: false,
      selectForward: true,
      maxDate: moment(),
      onSelect: (start, end) => {
        this.#handleDateUpdate(field, start, end);
      },
    });
    
    this.filters[field].datepicker = datepicker;
  }

  #setUpCheckbox(field) {
    const filterItem = this.filters[field];
    const checkboxes = filterItem.filter.querySelectorAll('input[data-class="checkbox"]');
    for (let i = 0; i < checkboxes.length; ++i) {
      const checkbox = checkboxes[i];
      checkbox.addEventListener('change', this.#handleCheckboxUpdate.bind(this));
    }
  }

  #setUpSearchbar(field) {
    const filterItem = this.filters[field];
    const searchbar = filterItem.filter.querySelector('input[data-class="searchbar"]');
    searchbar.addEventListener('keyup', this.#handleSearchbarUpdate.bind(this));
  }
  
  #setUpPagination(field) {
    if (!this.filters.hasOwnProperty(field)) {
      return;
    }

    const filterItem = this.filters[field];

    const previous = filterItem.filter.querySelector('a[data-value="previous"]');
    previous.addEventListener('click', this.#handlePaginationUpdate.bind(this));

    const next = filterItem.filter.querySelector('a[data-value="next"]');
    next.addEventListener('click', this.#handlePaginationUpdate.bind(this));

    const items = filterItem.filter.querySelectorAll('#page-items a:not([data-value="ignore"])');
    for (let i = 0; i < items.length; ++i) {
      items[i].addEventListener('click', this.#handlePaginationUpdate.bind(this));
    }
  }

  #setUpOptions(field) {
    const filterItem = this.filters[field];
    filterItem.filter.addEventListener('change', this.#handleOptionUpdate.bind(this));
  }

  // Private event handler methods
  #handleHistoryUpdate() {
    window.addEventListener('popstate', () => window.location.reload());
  }

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
    this.#postQuery();
  }

  #handleDateUpdate(field, start, end) {
    if (isNullOrUndefined(start) || isNullOrUndefined(end)) {
      return;
    }

    if (!start.isValid() || !end.isValid()) {
      return;
    }

    this.query[field] = [start.format(FILTER_DATEPICKER_FORMAT), end.format(FILTER_DATEPICKER_FORMAT)]
    this.#postQuery();
  }

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
      this.#postQuery();
      return;
    }

    if (index < 0) {
      return;
    }

    this.query[field].splice(index, 1);
    this.#postQuery();
    return;
  }

  #handleSearchbarUpdate(e) {
    const code = e.keyIdentifier || e.which || e.keyCode;
    if (code != FILTER_KEYCODES.ENTER) {
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
    this.#postQuery();
  }

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

    if (value === FILTER_PAGINATION.NEXT || value === FILTER_PAGINATION.PREVIOUS) {
      const offset = value === FILTER_PAGINATION.NEXT ? 1 : -1;
      const current = this.query.hasOwnProperty(field) ? this.query[field] : 1;
      value = current + offset;
    }

    value = parseInt(value);
    if (isNaN(value)) {
      return;
    }

    if (FILTER_SCROLL_TOP_ON_PAGE_CHANGE) {
      window.scroll({top: 0, left: 0, behavior: 'smooth'});
    }
    
    this.query[field] = value;
    this.#postQuery();
  }
}

domReady.finally(() => {
  const filters = new FilterService();
  window.filterService = filters;
});
