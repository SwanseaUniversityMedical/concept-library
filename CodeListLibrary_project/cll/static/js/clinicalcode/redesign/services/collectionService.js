const DETAIL_URL = '/ge/${id}/version/${version_id}/detail/';

const COLLECTION_HEADINGS = {
  PROFILE_COLLECTIONS: ['Name', 'Version ID', 'Updated', 'Owner', 'Status'],
  MODERATION_COLLECTIONS: ['Name', 'Version ID', 'Requested', 'Owner', 'Status']
};

const COLLECTION_TABLE_LIMITS = {
  PER_PAGE: 5,
  PER_PAGE_SELECT: [5, 10, 20]
};

const MAX_NAME_LENGTH = 50;

const COLLECTION_MAP = {
  PROFILE_COLLECTIONS: (item) => {
    return [
      `${item.id} - ${item.name}`, 
      item.history_id, 
      new Date(item.updated), 
      item.group_name || item.owner_name,
      item.publish_status
    ];
  },
  MODERATION_COLLECTIONS: (item) => {
    return [
      `${item.id} - ${item.name}`, 
      item.history_id, 
      new Date(item.created), 
      item.group_name || item.owner_name,
      item.publish_status
    ];
  }
}

const PUBLISH_STATUS_TAGS = [
  { text: 'REQUESTED', bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
  { text: 'PENDING',   bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
  { text: 'PUBLISHED', bg_colour: 'tertiary-accent', text_colour: 'accent-dark' }, 
  { text: 'REJECTED',  bg_colour: 'danger-accent',   text_colour: 'accent-dark' },
  { text: 'ARCHIVED',  bg_colour: 'dark-accent',     text_colour: 'accent-brightest' }, 
  { text: 'DRAFT',     bg_colour: 'washed-accent',   text_colour: 'accent-dark' }
];

/** getCollectionData
 * 
 * @desc Method that retrieves all relevant <data/> elements with
 *       its data-owner attribute pointing to the entity creator.
 * 
 * @returns {object} An object describing the data, with each key representing 
 *                   the name of the <data/> element
 */
const getCollectionData = () => {
  const values = document.querySelectorAll('data[data-owner="collection-service"]');

  const result = { };
  for (let i = 0; i < values.length; i++) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('type');
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
 * 
 * @param {*} data 
 * @param {*} id 
 * @param {*} version_id 
 * @returns 
 */
const renderNameAnchor = (data, id, version_id) => {
  const name = data.length > MAX_NAME_LENGTH 
    ? `${data.substring(0, MAX_NAME_LENGTH).trim()}...` 
    : data;

  const url = interpolateHTML(DETAIL_URL, {
    id: id,
    version_id: version_id
  });

  return `
    <a href='${url}'>${name}</a>
  `;
};

/**
 * 
 * @param {*} data 
 * @param {*} is_deleted 
 * @returns 
 */
const renderStatusTag = (pk, data, is_deleted) => {
  const tagData = (is_deleted === true) ? PUBLISH_STATUS_TAGS[4] : (PUBLISH_STATUS_TAGS?.[data] || PUBLISH_STATUS_TAGS[5]);
  
  return `
    <div class="meta-chip meta-chip-${tagData.bg_colour} meta-chip-center-text">
      <span class="meta-chip__name meta-chip__name-text-${tagData.text_colour} meta-chip__name-bold">
        ${tagData.text}
      </span>
    </div>
  `;
}

/**
 * 
 * @param {*} key 
 * @param {*} container 
 * @param {*} data 
 * @returns 
 */
const renderCollectionComponent = (pageType, key, container, data) => {
  if (isNullOrUndefined(data) || Object.keys(data).length == 0) {
    return;
  }
  
  const emptyCollection = container.parentNode.querySelector('#empty-collection');
  emptyCollection.classList.remove('show');
  
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
    },
    columns: [
      {
        select: 0,
        type: 'string',
        render: (value, id, rowIndex) => {
          const entity = data[rowIndex];
          
          return renderNameAnchor(value, entity.id, entity.history_id);
        },
      },
      { select: 1, type: 'number' },
      { 
        select: 2, 
        type: 'date', 
        format: 'YYYY-MM-DD',
        render: (value, id, rowIndex) => {
          return moment(value).format('YYYY-MM-DD');
        }
      },
      { select: 3, type: 'string' },
      { 
        select: 4, 
        type: 'number',
        render: (value, id, rowIndex) => {
          const entity = data[rowIndex];

          return renderStatusTag(entity.name, value, entity.is_deleted);
        } 
      },
    ],
    data: {
      headings: COLLECTION_HEADINGS?.[pageType],
      data: data.map(item => COLLECTION_MAP?.[pageType](item)),
    },
  });

  return datatable.columns.sort(2, 'desc');
};

domReady.finally(() => {
  const data = getCollectionData();
  for (let [key, value] of Object.entries(data)) {
    if (value.data.length < 1) {
      continue;
    }

    renderCollectionComponent(value.pageType, key, value.container, value.data);
  }
});
