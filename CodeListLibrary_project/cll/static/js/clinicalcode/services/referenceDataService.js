const
  /**
   * RDS_REFERENCE_TABLE_LIMITS
   * @desc describes the default params for the table element(s)
   * 
   */
  RDS_REFERENCE_TABLE_LIMITS = {
    PER_PAGE: 5,
    PER_PAGE_SELECT: [5, 25, 50]
  },
  /**
   * RDS_REFERENCE_HEADINGS
   * @desc describes the headings of the table(s)
   * 
   */
  RDS_REFERENCE_HEADINGS = ['index', 'ID', 'Name'];

/**
 * RDS_REFERENCE_MAP
 * @desc maps the reference item to a flat array
 * @param {object} item the item to map
 * @param {number} index the associated index
 * @returns {array} the mapped array
 * 
 */
const RDS_REFERENCE_MAP = (item, index) => {
  return [
    index,
    item.id,
    item.name
  ];
}

/** 
 * getReferenceData
 * @desc Method that retrieves all relevant <data/> elements with
 *       its data-owner attribute pointing to the entity creator.
 * 
 * @returns {object} An object describing the data, with each key representing 
 *                   the name of the <data/> element
 */
const getReferenceData = () => {
  const values = document.querySelectorAll('data[data-owner="reference-data-service"]');

  const result = { };
  for (let i = 0; i < values.length; i++) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('type');
    
    let value = data.innerText.trim();
    if (!isNullOrUndefined(value) && !isStringEmpty(value.trim())) {
      if (type == 'text/json') {
        value = JSON.parse(value);
      }
    }

    result[name] = {
      container: data.parentNode.querySelector('.reference-collection__table-container'),
      data: value || [ ]
    }
  }

  return result;
};

/**
 * renderReferenceComponent
 * @desc given the data associated with the `<data/>` elements,
 *       attempt to render the component(s) for each of the reference
 *       item(s)
 * 
 * @param {string|any} key the data associated key
 * @param {node} container the relevant container node
 * @param {object} data the associated data object
 * 
 */
const renderReferenceComponent = (key, container, data) => {
  if (isNullOrUndefined(data) || Object.keys(data).length == 0) {
    return;
  }
    
  const table = container.appendChild(createElement('table', {
    'id': `reference-datatable-${key}`,
    'class': 'reference-collection-table__wrapper',
  }));

  const datatable = new window.simpleDatatables.DataTable(table, {
    perPage: RDS_REFERENCE_TABLE_LIMITS.PER_PAGE,
    perPageSelect: RDS_REFERENCE_TABLE_LIMITS.PER_PAGE_SELECT,
    fixedColumns: false,
    classes: {
      wrapper: 'overflow-table-constraint',
    },
    columns: [
      { select: 0, type: 'number', hidden: true },
      { select: 1, type: 'number' },
      { select: 2, type: 'string' }
    ],
    data: {
      headings: RDS_REFERENCE_HEADINGS,
      data: data.map((item, index) => RDS_REFERENCE_MAP(item, index)),
    },
  });

  return datatable.columns.sort(1, 'asc');
};

/**
 * Main thread
 * @desc initialises the component(s) once the DOM resolves
 * 
 */
domReady.finally(() => {
  const data = getReferenceData();
  for (let [key, value] of Object.entries(data)) {
    if (value.data.length < 1) {
      continue;
    }

    renderReferenceComponent(key, value.container, value.data);
  }
});
