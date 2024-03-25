let ARCHIVE_TEMPLATE;

const
  /**
   * DETAIL_URL & UPDATE_URL
   * @desc describes the URL(s) associated with the action button(s)
   * 
   */
  DETAIL_URL = '/phenotypes/${id}/version/${version_id}/detail/',
  UPDATE_URL = '/update/${id}/${version_id}',
  /**
   * COLLECTION_HEADINGS
   * @desc describes the headings associated with each key's table
   * 
   */
  COLLECTION_HEADINGS = {
    PROFILE_COLLECTIONS: ['index', 'Name', 'ID', 'Version ID', 'Updated', 'Owner', 'Status'],
    MODERATION_COLLECTIONS: ['index', 'Name', 'ID', 'Version ID', 'Requested', 'Owner', 'Status']
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
  STATUSES = ['REQUESTED', 'PENDING', 'PUBLISHED', 'REJECTED', 'ARCHIVED', 'DRAFT'],
  /**
   * PUBLISH_STATUS_TAGS
   * @desc describes the attributes associated with a status
   * 
   */
  PUBLISH_STATUS_TAGS = [
    { text: 'REQUESTED', bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
    { text: 'PENDING',   bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
    { text: 'PUBLISHED', bg_colour: 'tertiary-accent', text_colour: 'accent-dark' }, 
    { text: 'REJECTED',  bg_colour: 'danger-accent',   text_colour: 'accent-dark' },
    { text: 'ARCHIVED',  bg_colour: 'dark-accent',     text_colour: 'accent-brightest' }, 
    { text: 'DRAFT',     bg_colour: 'washed-accent',   text_colour: 'accent-dark' }
  ];

/**
 * COLLECTION_MAP
 * @desc handler methods for mapping data into its respective table
 * 
 */
const COLLECTION_MAP = {
  PROFILE_COLLECTIONS: (item, index) => {
    let status;
    if (item.is_deleted) {
      status = -1;
    } else {
      status = (isNullOrUndefined(item.publish_status) || item.publish_status < 0) ? 5 : item.publish_status;
    }

    status = STATUSES[status] || 'ARCHIVED';

    return [
      index,
      `${item.id} - ${item.name}`,
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
      status = (isNullOrUndefined(item.publish_status) || item.publish_status < 0) ? 5 : item.publish_status;
    }

    status = STATUSES[status] || 'ARCHIVED';

    return [
      index,
      `${item.id} - ${item.name}`,
      item.id,
      item.history_id,
      new Date(item.updated),
      item.group_name || item.owner_name,
      status
    ];
  }
}

/**
 * getCollectionData
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
 * renderNameAnchor
 * @desc method to render the anchor associated with an element
 * @param {object} data the data associated with the element
 * @param {number|any} id the `id` of the element
 * @param {number|any} version_id the `version_id` of the element
 * @returns {string} returns the formatted render html target
 * 
 */
const renderNameAnchor = (pageType, key, entity) => {
  const { id, history_id, name, publish_status } = entity;

  let text = `${id} - ${name}`;
  text = text.length > MAX_NAME_LENGTH 
    ? `${text.substring(0, MAX_NAME_LENGTH).trim()}...` 
    : text;

  const brand = getBrandedHost();
  const url = interpolateString(brand + DETAIL_URL, {
    id: id,
    version_id: history_id
  });

  if (isNullOrUndefined(ARCHIVE_TEMPLATE) || pageType !== 'PROFILE_COLLECTIONS') {
    return `
      <a href='${url}'>${text}</a>
    `;
  }

  switch (key) {
    case 'content': {
      const update = interpolateString(brand + UPDATE_URL, {
        id: id,
        version_id: history_id
      });
    
      let target =  `
        <a href='${url}'>${text}</a>
        <span tooltip="Edit Phenotype" direction="left">
          <span class="profile-collection__edit-icon"
                tabindex="0"
                aria-label="Edit Phenotype"
                role="button"
                data-target="edit"
                data-href="${update}"></span>
        </span>
      `;
    
      if (publish_status != 2) {
        target += `
          <span tooltip="Archive Phenotype" direction="left">
            <span class="profile-collection__delete-icon"
                  tabindex="0" aria-label="Archive Phenotype"
                  role="button"
                  data-target="archive"
                  data-id="${id}"></span>
          </span>
        `;
      }
    
      return target;
    }

    case 'archived': {
      return `
        <a href='${url}'>${text}</a>
        <span tooltip="Restore Phenotype" direction="left">
          <span class="profile-collection__restore-icon"
                tabindex="0" aria-label="Restore Phenotype"
                role="button"
                data-target="restore"
                data-id="${id}"></span>
        </span>
      `;
    }

    default: {
      return `
        <a href='${url}'>${text}</a>
      `;
    }
  }
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
    return new Date(b.updated) - new Date(a.updated);
  });

  const datatable = new window.simpleDatatables.DataTable(table, {
    perPage: COLLECTION_TABLE_LIMITS.PER_PAGE,
    perPageSelect: COLLECTION_TABLE_LIMITS.PER_PAGE_SELECT,
    fixedColumns: false,
    classes: {
      wrapper: 'overflow-table-constraint',
    },
    template: (options, dom) => `<div class='${options.classes.top}'>
      <div class='${options.classes.dropdown}'>
        <label>
          <select class='${options.classes.selector}'></select> ${options.labels.perPage}
        </label>
      </div>
      <div class='${options.classes.search}'>
        <input id="column-searchbar" class='${options.classes.input}' placeholder='Search...' type='search' title='${options.labels.searchTitle}'${dom.id ? ` aria-controls="${dom.id}"` : ""}>
      </div>
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
          return renderNameAnchor(pageType, key, entity);
        },
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
      },
      { select: 5, type: 'string' },
      { 
        select: 6,
        type: 'string',
        render: (value, cell, rowIndex) => {
          return renderStatusTag(value);
        },
      },
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
    datatable.search(value, [1, 2, 3, 4, 5, 6]);
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
 * tryArchivePhenotype
 * @desc instantiates a modal that allows users to confirm
 *       whether they want to archive a phenotype; and then
 *       attempts to send a request to the server to archive a phenotype
 * 
 * @param {number} id the associated phenotype id
 * 
 */
const tryArchivePhenotype = (id) => {
  window.ModalFactory.create({
    title: `Are you sure you want to archive ${id}?`,
    content: ARCHIVE_TEMPLATE.innerHTML,
    onRender: (modal) => {
      const entityIdField = modal.querySelector('#id_entity_id');
      entityIdField.value = id;

      const passphraseField = modal.querySelector('#id_passphrase');
      passphraseField.setAttribute('placeholder', id);
    },
    beforeAccept: (modal) => {
      const form = modal.querySelector('#archive-form-area');
      return {
        form: new FormData(form),
        action: form.action,
      };
    }
  })
    .then((result) => {
      return fetch(result.data.action, {
        method: 'post',
        body: result.data.form,
      })
        .then(response => response.json())
        .then(response => {
          if (!response || !response?.success) {
            window.ToastFactory.push({
              type: 'warning',
              message: response?.message || 'Form Error',
              duration: 5000,
            });
            return;
          }

          window.location.reload();
        });
    })
    .catch((e) => {
      console.warn(e);
    });
}

/**
 * tryRestorePhenotype
 * @desc attempts to send a request to the server to restore a phenotype
 * @param {number} id the associated phenotype id
 * @returns {object<Promise>} returns the request promise
 * 
 */
const tryRestorePhenotype = (id) => {
  const token = getCookie('csrftoken');
  return fetch(
    window.location.href,
    {
      method: 'POST',
      cache: 'no-cache',
      credentials: 'same-origin',
      withCredentials: true,
      headers: {
        'X-CSRFToken': token,
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ restoration_id: id })
    }
  )
    .then(response => response.json())
    .then(response => {
      if (!response || !response?.success) {
        window.ToastFactory.push({
          type: 'warning',
          message: response?.message || 'Restoration Error',
          duration: 5000,
        });
        
        throw new Error(response?.message || 'Restoration Error');
      }
    });
}

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

  if (!isNullOrUndefined(ARCHIVE_TEMPLATE)) {
    document.addEventListener('click', (e) => {
      const target = e.target;
      if (!target.matches('[data-target]')) {
        return;
      }
  
      const trg = target.getAttribute('data-target');
      switch (trg) {
        case 'archive': {
          const id = target.getAttribute('data-id');
          tryArchivePhenotype(id);
        } break;
        
        case 'edit': {
          window.location.href = target.getAttribute('data-href');
        } break;

        case 'restore': {
          const id = target.getAttribute('data-id');
          window.ModalFactory.create({
            title: 'Are you sure?',
            content: `<p>Would you like to restore <strong>${id}</strong>?</p>`
          })
            .then((result) => {
              return tryRestorePhenotype(id);
            })
            .then(() => {
              window.location.reload();
            })
            .catch(console.warn);
        } break;
        
        default: break;
      }
    });
  }
});
