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
    item?.id ?? item?.value,
    item.name
  ];
}

/** 
 * getReferenceData
 * @desc Method that retrieves all relevant <script type="application/json" /> elements with
 *       its data-owner attribute pointing to the entity creator.
 * 
 * @returns {object} An object describing the data, with each key representing 
 *                   the name of the <script type="application/json" /> element
 */
const getReferenceData = () => {
  const values = document.querySelectorAll('script[type="application/json"][data-owner="reference-data-service"]');

  const result = { };
  for (let i = 0; i < values.length; i++) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('desc-type');
    
    let value = data.innerText.trim();
    if (!isNullOrUndefined(value) && !isStringEmpty(value.trim())) {
      if (type == 'text/json') {
        value = JSON.parse(value);
      }
    }

    let container = data.parentNode.querySelector('.reference-collection__table-container');
    if (isNullOrUndefined(container)) {
      container = data.parentNode; 
    }

    result[name] = {
      container: container,
      data: value || [ ]
    }
  }

  return result;
};

/**
 * renderTreeViewComponent
 * @desc given the data associated with the `<script type="application/json" />` elements,
 *       attempt to render a tree view component for the
 *       ontology API
 * 
 * @param {string|any} key the data associated key
 * @param {node} container the relevant container node
 * @param {object} groups the associated data object
 * @returns 
 */
const renderTreeViewComponent = async (key, container, _groups) => {
  const sources = await fetch(
    `${getBrandedHost()}/api/v1/ontology/`,
    {
      method: 'GET',
      headers: {
        'X-Target': 'get_options',
        'X-Requested-With': 'XMLHttpRequest',
      }
    }
  )
    .then(response => {
      if (!response.ok) {
        throw new Error(`Failed to GET ontology options with Err<code: ${response.status}> and response:\n${response}`);
      }

      return response.json();
    })
    .then(dataset => {
      if (!(dataset instanceof Object) || !Array.isArray(dataset)) {
        throw new Error(`Expected ontology init data to be an object with a result array, got ${dataset}`);
      }

      return dataset;
    });

  if (!Array.isArray(sources)) {
    console.warn('Failed to load tree component with err:', sources);
    return;
  }
  
  const tabItems = container.querySelector('#tab-items');
  const tabContent = container.querySelector('#tab-content');

  let selectedIndex;
  const fetchNodeData = async (id) => {
    if (isNullOrUndefined(selectedIndex) || typeof(selectedIndex) !== 'number') {
      throw new Error(`Expected valid numerical source, got ${typeof(selectedIndex)}`); 
    }

    const url = `/api/v1/ontology/node/${id}`;
    const response = await fetch(url, { method: 'GET' });
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

    return res;
  }

  const createViewer = (selected) => {
    let sourceIndex = sources.findIndex(x => x?.model?.source == selected)
    if (sourceIndex < 0) {
      return;
    }

    const source = sources[sourceIndex];
    selectedIndex = selected;
    clearAllChildren(tabContent);

    const viewer = tabContent.appendChild(
      createElement('div', {
        'className': 'slim-scrollbar',
        'style': 'max-height: 400px; overflow-y: auto; overflow-x: none;',
      })
    );

    const tabs = tabItems.querySelectorAll('button');
    for (let i = 0; i < tabs.length; ++i) {
      const tab = tabs[i];
      const dataId = tab.getAttribute('data-id');
      if (dataId === selectedIndex.toString()) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    }

    const tree = eleTree({
      el: viewer,
      lazy: true,
      sort: true,
      data: source.nodes,
      showCheckbox: false,
      highlightCurrent: true,
      icon: {
        checkFull: '.eletree_icon-check_full',
        checkHalf: '.eletree_icon-check_half',
        checkNone: '.eletree_icon-check_none',
        dropdownOff: '.eletree_icon-dropdown_right',
        dropdownOn: '.eletree_icon-dropdown_bottom',
        loading: '.eleTree-animate-rotate.eletree_icon-loading1',
      },
      customText: (data) => {
        return `<span class="ref-ontology-node">
          <span>
            ${data.label}
          </span>
          <span class="ref-ontology-node__source">
            <b>NodeID:</b>
            <b>${data.id}</b>
          </span>
        </span>`;
      }
    });

    tree.on('lazyload', (group) => {
      const { data, load } = group;
      const sourceId = data?.type_id;
      const dataIndex = sources.findIndex(e => e?.model?.source == sourceId);
      const dataset = dataIndex >= 0 ? sources[dataIndex] : null;
      if (isNullOrUndefined(dataset)) {
        return;
      }

      fetchNodeData(data.id)
        .then(async node => load(node.children))
        .catch(console.error);
    });

    return tree;
  };

  for (let i = 0; i < sources.length; ++i) {
    const item = sources[i];
    if (typeof item !== 'object') {
      continue;
    }

    const nodes = item.nodes;
    const model = !!item?.model && typeof item.model === 'object' ? item.model : { };
    const sourceId = model?.source;
    const sourceLabel = model?.label;
    if (typeof sourceId !== 'number' || typeof sourceLabel !== 'string' || !Array.isArray(nodes)) {
      continue;
    }

    if (typeof selectedIndex !== 'number') {
      selectedIndex = sourceId;
    }

    const doc = parseHTMLFromString(`
      <button aria-label="tab" data-id="${sourceId}" class="tab-view__tab ${i == selectedIndex ? 'active' : ''}">
        ${sourceLabel}
      </button>
    `, true);

    const elem = tabItems.appendChild(doc[0]);
    elem.addEventListener('click', () => {
      createViewer(sourceId);
    });
  }

  return createViewer(selectedIndex);
}

const renderTableViewComponent = (container, data) => {
  const referenceTemplate = document.querySelector('[data-name="reference-data"]');

  container.innerHTML = "";
  for (const [index, value] of Object.entries(data)) {
    const [tableContainer] = composeTemplate(referenceTemplate, {
      params: {
        name: value.name,
        description: value.description,
      },
      render: (elem) => {
        elem = elem.shift();
        elem = container.appendChild(elem);

        const refContainer = elem.querySelector('#ref-container');
        const table = refContainer.appendChild(createElement('table', {
          'id': `reference-datatable-${index}`,
          'class': 'reference-collection-table__wrapper',
        }));
      
        const datatable = new window.simpleDatatables.DataTable(table, {
          perPage: RDS_REFERENCE_TABLE_LIMITS.PER_PAGE,
          perPageSelect: RDS_REFERENCE_TABLE_LIMITS.PER_PAGE_SELECT,
          fixedColumns: true,
          classes: {
            wrapper: 'overflow-table-constraint',
            container: 'datatable-container slim-scrollbar',
          },
          columns: [
            { select: 0, type: 'number', hidden: true },
            { select: 1, type: 'number' },
            { select: 2, type: 'string' }
          ],
          data: {
            headings: RDS_REFERENCE_HEADINGS,
            data: value.options.map((item, index) => RDS_REFERENCE_MAP(item, index)),
          },
        });
      
        datatable.columns.sort(1, 'asc');
      },
    });
  }
}

/**
 * renderReferenceComponent
 * @desc given the data associated with the `<script type="application/json" />` elements,
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

  const componentType = container.getAttribute('type');
  if (componentType === 'tree') {
    // tree view
    return renderTreeViewComponent(key, container, data);
  }

  // list view
  return renderTableViewComponent(container, data);
};

const getTemplateData = async ({ url, req, ctrl, params }) => {
  const token = getCookie('csrftoken');

  req = mergeObjects(
    isObjectType(req) ? req : { },
    {
      method: 'GET',
      credentials: 'same-origin',
      withCredentials: true,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': token,
        'Authorization': `Bearer ${token}`,
        'Pragma': 'max-age=3600',
        'Cache-Control': 'max-age=3600',
      },
    },
    false,
    true
  );

  ctrl = mergeObjects(
    isObjectType(ctrl) ? ctrl : { },
    {
      retries: 1,
      backoff: 100,
      onError: (_err, retryCount, remainingTries) => {
        if (retryCount > 1 && remainingTries < 1) {
          window.ToastFactory.push({
            type: 'danger',
            message: `We've not been able to connect to the server, please refresh the page and try again.`,
            duration: 7000,
          });
        }

        return true;
      },
      beforeAccept: (response, _retryCount, _remainingTries) => response.ok,
    }
  );

  if (isObjectType(params)) {
    params = new URLSearchParams(params);
  }

  if (!isNullOrUndefined(params) && !params instanceof URLSearchParams) {
    params = '?' + params;
  } else {
    params = '';
  }

  if (!stringHasChars(url)) {
    url = getCurrentURL();
  }

  const response = await fetchWithCtrl(
    url + params,
    req,
    ctrl,
  );

  if (response instanceof Error) {
    throw response;
  }

  if (!response.ok) {
    let msg;
    try {
      msg = await response.json();
      msg = stringHasChars(msg?.message) ? msg.message : String(response);
    } catch {
      msg = String(response);
    }

    throw new Error(`Failed to retrieve Template data with Err<code: ${response.status}> and message:\n${msg}`);
  }

  const results = await response.json();
  if (isNullOrUndefined(results) || !isObjectType(results) || isNullOrUndefined(results?.data)) {
    const msg = `${typeof results}<data: ${isObjectType(results) ? typeof results?.data : 'null'}>`;
    throw new Error('Expected response to describe an Object containing a \'data\' key but got result: ' + msg);
  }

  return results;
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

  const templateSelector = document.querySelector('#template-selector');
  templateSelector.addEventListener('change', (e) => {
    const selected = e.target.value;

    getTemplateData({
      req: {
        method: 'OPTIONS',
        body: JSON.stringify({
          template_id: selected
        }),
      },
      ctrl: {
        retries: 2,
      }
    })
      .then(result => {
        renderReferenceComponent(
          null,
          document.querySelector('#template-fields'),
          result.data
        )
      })
      .catch(console.error);
  });
});
