let ARCHIVE_TEMPLATE;

const
  /**
   * DETAIL_URL
   * @desc describes the URL(s) associated with the action button(s)
   * 
   */
  DETAIL_URL = '/org/view/${slug}/',
  /**
   * COLLECTION_HEADINGS
   * @desc describes the headings associated with each key's table
   * 
   */
  COLLECTION_HEADINGS = {
    OWNED_ORG_COLLECTIONS: ['index', 'ID', 'Name', 'Slug'],
    MEMBER_ORG_COLLECTIONS: ['index', 'ID', 'Name', 'Slug']
  },
  /**
   * COLLECTION_TABLE_LIMITS
   * @desc describes the default params for each table
   * 
   */
  COLLECTION_TABLE_LIMITS = {
    PER_PAGE: 5,
    PER_PAGE_SELECT: [5, 10, 20]
  },
  /**
   * MAX_NAME_LENGTH
   * @desc describes the max length of a name field
   * 
   */
  MAX_NAME_LENGTH = 50;

/**
 * COLLECTION_MAP
 * @desc handler methods for mapping data into its respective table
 * 
 */
const COLLECTION_MAP = {
  OWNED_ORG_COLLECTIONS: (item, index) => {
    return [
      index,
      item.id,
      `${strictSanitiseString(item.name)}`,
      item.slug
    ];
  },
  MEMBER_ORG_COLLECTIONS: (item, index) => {
    return [
      index,
      item.id,
      `${strictSanitiseString(item.name)}`,
      item.slug
    ];
  }
}

/**
 * renderNameAnchor
 * @desc method to render the anchor associated with an element
 * @param {object} data the data associated with the element
 * @param {number|any} id the `id` of the element
 * @param {number|any} version_id the `version_id` of the element
 * @returns {string} returns the formatted render html target
 * 
 */
const renderNameAnchor = (pageType, key, entity) => {
  const { id, name, slug } = entity;

  let text = `${strictSanitiseString(name)}`;
  text = text.length > MAX_NAME_LENGTH 
    ? `${text.substring(0, MAX_NAME_LENGTH).trim()}...` 
    : text;

  const brand = getBrandedHost();
  const url = interpolateString(brand + DETAIL_URL, {
    slug: slug
  });

  return `
    <a href='${url}'>${text}</a>
  `;
};

/**
 * getCollectionData
 * @desc Method that retrieves all relevant <script type="application/json" /> elements with
 *       its data-owner attribute pointing to the entity creator.
 * 
 * @returns {object} An object describing the data, with each key representing 
 *                   the name of the <script type="application/json" /> element
 */
const getCollectionData = () => {
  const values = document.querySelectorAll('script[type="application/json"][data-owner="organisation-service"]');

  const result = { };
  for (let i = 0; i < values.length; i++) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('desc-type');
    const pageType = data.getAttribute('page-type');

    let value = data.innerText.trim();
    if (!isNullOrUndefined(value) && !isStringEmpty(value.trim())) {
      if (type == 'text/json') {
        value = JSON.parse(value);
      }
    }

    result[name] = {
      pageType: pageType,
      container: data.parentNode.querySelector('.profile-collection__table-container'),
      data: value || [ ]
    }
  }

  return result;
};

/**
 * renderCollectionComponent
 * @desc method to render the collection component
 * @param {string} pageType the component page type, e.g. in the case of profile/moderation pages
 * @param {string} key the component type associated with this component, e.g. collection
 * @param {node} container the container node associated with this element
 * @param {object} data the data associated with this element
 * 
 */
const renderCollectionComponent = (pageType, key, container, data) => {
  if (isNullOrUndefined(data) || Object.keys(data).length == 0) {
    return;
  }
  
  const emptyCollection = container.parentNode.querySelector('#empty-collection');
  if (!isNullOrUndefined(emptyCollection)) {
    emptyCollection.classList.remove('show');
  }
  
  const table = container.appendChild(createElement('table', {
    'id': `collection-datatable-${key}`,
    'class': 'profile-collection-table__wrapper',
  }));

  const datatable = new window.simpleDatatables.DataTable(table, {
    perPage: COLLECTION_TABLE_LIMITS.PER_PAGE,
    perPageSelect: COLLECTION_TABLE_LIMITS.PER_PAGE_SELECT,
    fixedColumns: false,
    classes: {
      wrapper: 'overflow-table-constraint',
      container: 'datatable-container slim-scrollbar',
    },
    template: (options, dom) => `
    <div class='${options.classes.top}'>
      <div class='${options.classes.dropdown}'>
        <label>
          <select class='${options.classes.selector}'></select> ${options.labels.perPage}
        </label>
      </div>
      <div class='${options.classes.search}'>
        <input id="column-searchbar" class='${options.classes.input}' placeholder='Search...' type='search' title='${options.labels.searchTitle}'${dom.id ? ` aria-controls="${dom.id}"` : ""}>
      </div>
      <div class='${options.classes.container}'${options.scrollY.length ? ` style='height: ${options.scrollY}; overflow-Y: auto;'` : ""}></div>
      <div class='${options.classes.bottom}'>
      <div class='${options.classes.info}'></div>
      <nav class='${options.classes.pagination}'></nav>
    </div>`,
    columns: [
      { select: 0, type: 'number', hidden: true },
      { 
        select: 1, 
        type: 'number', 
        render: (value, cell, rowIndex) => {
          const entity = data.find(e => e.id == value);
          return renderNameAnchor(pageType, key, entity);
        }, 
      },
      { select: 2, type: 'string', hidden: true },
      { select: 3, type: 'string', hidden: true }
    ],
    tableRender: (_data, table, type) => {
      if (type === 'print' || key !== 'content') {
        return table
      }

      const header = table.childNodes[0];
      header.childNodes = header.childNodes[0].childNodes.map((_th, index) => {
        if (index < 4) {
          return _th;
        }

        return {
          nodeName: 'TH',
          attributes: {
            'column-index': index + 2,
            'heading': COLLECTION_HEADINGS?.[pageType][index + 2],
          },
          childNodes: [
            {
              nodeName: 'select',
              attributes: {
                'class': 'selection-input',
                'data-js-filter': 'true',
                'data-columns': `[${index}]`,
              },
            }
          ]
        }
      });

      return table;
    },
    data: {
      headings: COLLECTION_HEADINGS?.[pageType],
      data: data.map((item, index) => COLLECTION_MAP?.[pageType](item, index)),
    },
  });

  const searchbar = datatable.wrapperDOM.querySelector('#column-searchbar');
  searchbar.addEventListener('change', (event) => {
    event.stopPropagation();
    event.preventDefault();

    const value = event.target.value;
    if (isStringEmpty(value)) {
      datatable.search('', undefined);
      return;
    }
    datatable.search(value, [1, 2, 3, 4]);
  });
  
  table.querySelectorAll('[data-js-filter]').forEach(select => {
    let head = select.closest('th');
    let columnIndex = head.getAttribute('column-index');
    columnIndex = parseInt(columnIndex);

    let uniqueValues = [...new Set(datatable.data.data.map(tr => tr[columnIndex].data))];
    let option = document.createElement('option');
    option.value = '-1';
    option.selected = true;
    option.hidden = true;
    option.textContent = head.getAttribute('heading');
    select.appendChild(option);
    
    uniqueValues.forEach((value) => {
      const option = document.createElement('option');
      option.textContent = value;
      option.value = value;
      select.appendChild(option);
    });

    select.addEventListener('change', (event) => {
      const selectedValue = event.target.value;
      if (selectedValue) {
        let params = [{term: selectedValue, columns: [columnIndex]}];
        datatable.multiSearch(params);
        return;
      }

      datatable.search('', undefined);
    });
  });

  datatable.columns.sort(2, 'desc');
};

/**
 * Main thread
 * @desc initialises the component(s) once the DOM resolves
 * 
 */
domReady.finally(() => {
  ARCHIVE_TEMPLATE = document.querySelector('#archive-form');

  const data = getCollectionData();
  for (let [key, value] of Object.entries(data)) {
    if (value.data.length < 1) {
      continue;
    }

    renderCollectionComponent(value.pageType, key, value.container, value.data);
  }
});
