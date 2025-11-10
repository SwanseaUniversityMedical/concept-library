import * as orgUtils from './utils.js';

let ARCHIVE_TEMPLATE;

const
  /**
   * ENTITY_URL
   * @desc specifies the URL(s) associated with the "Popular" card
   */
  ENTITY_URL = '/${url_target}/${id}/detail/',
  /**
   * DETAIL_URL
   * @desc describes the URL(s) associated with the action button(s)
   * 
   */
  DETAIL_URL = '/${url_target}/${id}/version/${version_id}/detail/',
  /**
   * COLLECTION_HEADINGS
   * @desc describes the headings associated with each key's table
   * 
   */
  COLLECTION_HEADINGS = {
    PUBLISHED_COLLECTIONS: ['index', 'Name', 'ID', 'Version ID', 'Updated'],
    DRAFT_COLLECTIONS: ['index', 'Name', 'ID', 'Version ID', 'Updated'],
    MODERATION_COLLECTIONS: ['index', 'Name', 'ID', 'Version ID', 'Updated']
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
  MAX_NAME_LENGTH = 50,
  /**
   * STATUSES
   * @desc describes the status element name(s)
   * 
   */
  STATUSES = ['REQUESTED', 'PENDING', 'PUBLISHED', 'REJECTED'],
  /**
   * PUBLISH_STATUS_TAGS
   * @desc describes the attributes associated with a status
   * 
   */
  PUBLISH_STATUS_TAGS = [
    { text: 'REQUESTED', bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
    { text: 'PENDING',   bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
    { text: 'PUBLISHED', bg_colour: 'tertiary-accent', text_colour: 'accent-dark' }, 
    { text: 'REJECTED',  bg_colour: 'danger-accent',   text_colour: 'accent-dark' }
  ];

/**
 * COLLECTION_MAP
 * @desc handler methods for mapping data into its respective table
 * 
 */
const COLLECTION_MAP = {
  PUBLISHED_COLLECTIONS: (item, index) => {
    return [
      index,
      `${item.id} - ${strictSanitiseString(item.name)}`,
      item.id,
      item.history_id,
      new Date(item.updated)
    ];
  },
  DRAFT_COLLECTIONS: (item, index) => {
    return [
      index,
      `${item.id} - ${strictSanitiseString(item.name)}`,
      item.id,
      item.history_id,
      new Date(item.updated)
    ];
  },
  MODERATION_COLLECTIONS: (item, index) => {    
    let status = (isNullOrUndefined(item.publish_status) || item.publish_status < 0) ? 5 : item.publish_status;
    status = STATUSES[status];

    return [
      index,
      `${item.id} - ${strictSanitiseString(item.name)}`,
      item.id,
      item.history_id,
      new Date(item.created)//,
      //status
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
const renderNameAnchor = (pageType, key, entity, mapping) => {
  const { id, history_id, name, publish_status } = entity;

  let urlTarget = mapping?.phenotype_url;
  if (!stringHasChars(urlTarget)) {
    urlTarget = 'phenotypes';
  }

  let text = `${id} - ${strictSanitiseString(name)}`;
  text = text.length > MAX_NAME_LENGTH 
    ? `${text.substring(0, MAX_NAME_LENGTH).trim()}...` 
    : text;

  const brand = getBrandedHost();
  const url = interpolateString(brand + DETAIL_URL, {
    id: id,
    version_id: history_id,
    url_target: urlTarget,
  });

  return `
    <a href='${url}' target=_blank rel="noopener">${text}</a>
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
        try {
          value = JSON.parse(value);
        } catch (e) {
          console.error(`Failed to parse data<index: ${i}, name: ${name}> w/ err:\n${e}`);
          value = null;
        }
      }
    }

    if (isNullOrUndefined(value) || !(Array.isArray(value) || isObjectType(value))) {
      value = null;
    }

    result[name] = {
      pageType: pageType,
      container: data.parentNode.querySelector('[data-cx="container"]'),
      data: value,
    }
  }

  return result;
};

/**
 * renderStatusTag
 * @desc method to render the status associated with an element
 * @param {object} data the data associated with the element
 * @param {boolean|any} is_deleted whether that item is considered to be deleted
 * @returns {string} the html render target
 * 
 */
const renderStatusTag = (data) => {
  let tagData = STATUSES.findIndex(e => e == data);
  tagData = PUBLISH_STATUS_TAGS[tagData];

  return `
    <div class="meta-chip meta-chip-${tagData.bg_colour} meta-chip-center-text">
      <span class="meta-chip__name meta-chip__name-text-${tagData.text_colour} meta-chip__name-bold">
        ${tagData.text}
      </span>
    </div>
  `;
}

/**
 * renderCollectionComponent
 * @desc method to render the collection component
 * @param {string} pageType the component page type, e.g. in the case of profile/moderation pages
 * @param {string} key the component type associated with this component, e.g. collection
 * @param {node} container the container node associated with this element
 * @param {object} data the data associated with this element
 * 
 */
const renderCollectionComponent = (pageType, key, container, data, mapping) => {
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

  data.sort((a, b) => {
    return new Date(b.updated) - new Date(a.updated);
  });

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
        type: 'string',
        render: (value, cell, rowIndex) => {
          const [entityId, ...others] = value.match(/^\w+-?/g);
          const entity = data.find(e => e.id == entityId);
          return renderNameAnchor(pageType, key, entity, mapping);
        }
      },
      { select: 2, type: 'number', hidden: true },
      { select: 3, type: 'number' },
      { 
        select: 4, 
        type: 'date', 
        format: 'YYYY-MM-DD',
        render: (value, cell, rowIndex) => {
          return moment(value).format('YYYY-MM-DD');
        }
      }
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
  const mapping = data.mapping.data;
  delete data.mapping;

  for (let [key, value] of Object.entries(data)) {
    if (isNullOrUndefined(value.data) || (Array.isArray(value.data) && value.data.length < 1)) {
      continue;
    }

    if (value.pageType === 'STATS') {
      if (!isObjectType(value.data)) {
        continue;
      }

      let entityResolver = (id) => {
        let urlTarget = mapping?.phenotype_url;
        if (!stringHasChars(urlTarget)) {
          urlTarget = 'phenotypes';
        }

        const brand = getBrandedHost();
        return interpolateString(brand + ENTITY_URL, {
          id: id,
          url_target: urlTarget,
        });
      }

      for (const key in value.data) {
        console.log(key, value.data[key], value.container)
        orgUtils.composeStatsCard(value.container, key, value.data[key], entityResolver)
      }
      continue;
    }

    renderCollectionComponent(value.pageType, key, value.container, value.data, mapping);
  }

  const leaveButton = document.querySelector('#leave-btn');
  if (!isNullOrUndefined(leaveButton)) {
    const token = getCookie('csrftoken');

    leaveButton.addEventListener('click', (e) => {
      orgUtils.confirmationPrompt({
        title: 'Are you sure?',
        content: '<p>You will lose access to this organisation and it\'s content</p>',
        onAccept: () => {
          return fetch(getCurrentURL(), {
            method: 'POST',
            cache: 'no-cache',
            credentials: 'same-origin',
            withCredentials: true,
            headers: {
              'X-Target': 'leave_organisation',
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': token,
              'Authorization': `Bearer ${token}`
            }
          })
            .then(response => response.json())
            .then(response => {
              if (response.status) {
                window.location.reload();
              }
            })
        }
      });
    });
  }
});
