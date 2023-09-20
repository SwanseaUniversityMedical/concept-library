const REFERENCE_TABLE_LIMITS = {
  PER_PAGE: 5,
  PER_PAGE_SELECT: [5, 25, 50]
};

const REFERENCE_HEADINGS = ['index', 'ID', 'Name']

const REFERENCE_MAP = (item, index) => {
  return [
    index,
    item.id,
    item.name
  ];
}

/** getReferenceData
 * 
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
 * 
 * @param {*} key 
 * @param {*} container 
 * @param {*} data 
 * @returns 
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
    perPage: REFERENCE_TABLE_LIMITS.PER_PAGE,
    perPageSelect: REFERENCE_TABLE_LIMITS.PER_PAGE_SELECT,
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
      headings: REFERENCE_HEADINGS,
      data: data.map((item, index) => REFERENCE_MAP(item, index)),
    },
  });

  return datatable.columns.sort(1, 'asc');
};

domReady.finally(() => {
  const data = getReferenceData();
  for (let [key, value] of Object.entries(data)) {
    if (value.data.length < 1) {
      continue;
    }

    renderReferenceComponent(key, value.container, value.data);
  }
});
