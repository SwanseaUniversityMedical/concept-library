const DETAIL_URL = '/phenotypes/${id}/version/${version_id}/detail/'

const COLLECTION_HEADINGS = {
  PROFILE_COLLECTIONS: ['Name', 'ID', 'Version ID', 'Updated', 'Owner', 'Status'],
  MODERATION_COLLECTIONS: ['Name', 'ID', 'Version ID', 'Requested', 'Owner', 'Status']
};

const COLLECTION_TABLE_LIMITS = {
  PER_PAGE: 5,
  PER_PAGE_SELECT: [5, 10, 20]
};

const MAX_NAME_LENGTH = 50;

const COLLECTION_MAP = {
  PROFILE_COLLECTIONS: (item, index) => {
    let status;
    if (item.is_deleted) {
      status = -1;
    } else {
      status = item.publish_status < 0 ? 5 : item.publish_status;
    }

    return [
      index,
      item.id,
      item.history_id,
      new Date(item.updated), 
      item.group_name || item.owner_name,
      status
    ];
  },
  MODERATION_COLLECTIONS: (item, index) => {    
    let status;
    if (item.is_deleted) {
      status = -1;
    } else {
      status = item.publish_status < 0 ? 5 : item.publish_status;
    }

    return [
      index,
      item.id,
      item.history_id,
      new Date(item.updated),
      item.group_name || item.owner_name,
      status
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
const renderNameAnchor = (entity) => {
  const { id, history_id, name } = entity;

  let text = `${id} - ${name}`;
  text = text.length > MAX_NAME_LENGTH 
    ? `${text.substring(0, MAX_NAME_LENGTH).trim()}...` 
    : text;

  const brand = getCurrentBrandPrefix();
  const url = interpolateHTML(brand + DETAIL_URL, {
    id: id,
    version_id: history_id
  });

  return `
    <a href='${url}'>${text}</a>
  `;
};

/**
 * 
 * @param {*} data 
 * @param {*} is_deleted 
 * @returns 
 */
const renderStatusTag = (data) => {
  const tagData = (data === -1) ? PUBLISH_STATUS_TAGS[4] : (PUBLISH_STATUS_TAGS?.[data] || PUBLISH_STATUS_TAGS[5]);
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

  data.sort((a, b) => {
    let id0 = parseInt(a.id.match(/\d+/)[0]);
    let id1 = parseInt(b.id.match(/\d+/)[0]);
    return id0 - id1;
  });

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
        type: 'number',
        render: (value, cell, rowIndex) => {
          const entity = data[value];
          return renderNameAnchor(entity);
        },
      },
      { select: 1, type: 'number', hidden: true },
      { select: 2, type: 'number' },
      { 
        select: 3, 
        type: 'date', 
        format: 'YYYY-MM-DD',
        render: (value, cell, rowIndex) => {
          return moment(value).format('YYYY-MM-DD');
        }
      },
      { select: 4, type: 'string' },
      { 
        select: 5,
        type: 'number',
        render: (value, cell, rowIndex) => {
          return renderStatusTag(value);
        }
      },
    ],
    data: {
      headings: COLLECTION_HEADINGS?.[pageType],
      data: data.map((item, index) => COLLECTION_MAP?.[pageType](item, index)),
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
