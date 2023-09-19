const DETAIL_URL = '/phenotypes/${id}/version/${version_id}/detail/'
const UPDATE_URL = '/update/${id}/${version_id}';

const COLLECTION_HEADINGS = {
  PROFILE_COLLECTIONS: ['Name', 'ID', 'Version ID', 'Updated', 'Owner', 'Status'],
  MODERATION_COLLECTIONS: ['Name', 'ID', 'Version ID', 'Requested', 'Owner', 'Status']
};

const COLLECTION_TABLE_LIMITS = {
  PER_PAGE: 5,
  PER_PAGE_SELECT: [5, 10, 20]
};

let ARCHIVE_TEMPLATE;
const MAX_NAME_LENGTH = 50;

const STATUSES = ['REQUESTED', 'PENDING', 'PUBLISHED', 'REJECTED', 'ARCHIVED', 'DRAFT'];
const PUBLISH_STATUS_TAGS = [
  { text: 'REQUESTED', bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
  { text: 'PENDING',   bg_colour: 'bubble-accent',   text_colour: 'accent-dark' }, 
  { text: 'PUBLISHED', bg_colour: 'tertiary-accent', text_colour: 'accent-dark' }, 
  { text: 'REJECTED',  bg_colour: 'danger-accent',   text_colour: 'accent-dark' },
  { text: 'ARCHIVED',  bg_colour: 'dark-accent',     text_colour: 'accent-brightest' }, 
  { text: 'DRAFT',     bg_colour: 'washed-accent',   text_colour: 'accent-dark' }
];

const COLLECTION_MAP = {
  PROFILE_COLLECTIONS: (item, index) => {
    let status;
    if (item.is_deleted) {
      status = -1;
    } else {
      status = (!item.publish_status || item.publish_status < 0) ? 5 : item.publish_status;
    }

    status = STATUSES[status] || 'ARCHIVED';

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
      status = (!item.publish_status || item.publish_status < 0) ? 5 : item.publish_status;
    }

    status = STATUSES[status] || 'ARCHIVED';

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
const renderNameAnchor = (pageType, key, entity) => {
  const { id, history_id, name, publish_status } = entity;

  let text = `${id} - ${name}`;
  text = text.length > MAX_NAME_LENGTH 
    ? `${text.substring(0, MAX_NAME_LENGTH).trim()}...` 
    : text;

  const brand = getCurrentBrandPrefix();
  const url = interpolateHTML(brand + DETAIL_URL, {
    id: id,
    version_id: history_id
  });

  if (isNullOrUndefined(ARCHIVE_TEMPLATE) || pageType !== 'PROFILE_COLLECTIONS' || key !== 'content') {
    return `
      <a href='${url}'>${text}</a>
    `;
  }

  const update = interpolateHTML(brand + UPDATE_URL, {
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
};

/**
 * 
 * @param {*} data 
 * @param {*} is_deleted 
 * @returns 
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
          return renderNameAnchor(pageType, key, entity);
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
            'column-index': index + 1,
            'heading': COLLECTION_HEADINGS?.[pageType][index + 1],
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
  
  table.querySelectorAll('[data-js-filter]').forEach(select => {
    let head = select.closest('th')
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
        let params = [{term: selectedValue, columns: [columnIndex]}]
        datatable.multiSearch(params);
      } else {
        datatable.search('', undefined)
      }
    });
  })

  return datatable.columns.sort(2, 'desc');
};

const tryArchivePhenotype = (id) => {
  window.ModalFactory.create({
    title: `Are you sure you want to archive ${id}?`,
    content: ARCHIVE_TEMPLATE.innerHTML,
    onRender: (modal) => {
      const entityIdField = modal.querySelector('#id_entity_id');
      entityIdField.value = id;
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
        default: break;
      }
    });
  }
});
