/**
 * ES_DEFAULT_DESCRIPTOR
 * @desc Default description string if none provided
 */
const ES_DEFAULT_DESCRIPTOR = 'Create a ${name}'

/**
 * getDescriptor
 * @desc gets the descriptor if valid, otherwise uses default format
 * @param {string} description the description associated with the item
 * @param {string} name the name associated with the item
 * @returns {string} the formatted descriptor
 * 
 */
const getDescriptor = (description, name) => {
  if (!isNullOrUndefined(description) && !isStringEmpty(description)) {
    return description;
  }

  return new Function('name', `return \`${ES_DEFAULT_DESCRIPTOR}\`;`)(name);
}

/**
 * createGroup
 * @desc method to interpolate a card using a template
 * 
 * @param {node}   container   the container element
 * @param {string} template    the template fragment
 * @param {number} entityLen   the num. of creatable entities
 * @param {number} id          the id of the associated element
 * @param {string} title       string, as formatted by the `getDescriptor` method
 * @param {string} description string, as formatted by the `getDescriptor` method
 * 
 * @returns {node} the interpolated element after appending to the container node
 * 
 */
const createGroup = (container, template, entityLen, id, title, description) => {
  let descCls;
  if (entityLen > 1) {
    title = title.toLocaleUpperCase();
    descCls = '';
    description = getDescriptor(description, title);
  } else {
    title = 'Please select:'
    descCls = 'hide';
    description = '';
  }

  const html = interpolateString(template, {
    'id': id,
    'title': title,
    'description': description,
    'descCls': descCls,
  });

  const doc = parseHTMLFromString(html, true);
  return container.appendChild(doc[0]);
}

/**
 * createCard
 * @desc method to interpolate a card using a template
 * @param {node} container the container element
 * @param {string} template the template fragment
 * @param {number} id the id of the associated element
 * @param {any} type any data value relating to the type of the element
 * @param {string} hint a string that defines the hint text of the element
 * @param {string} title string, as formatted by the `getDescriptor` method
 * @param {string} description string, as formatted by the `getDescriptor` method
 * @returns {node} the interpolated element after appending to the container node
 * 
 */
const createCard = (container, template, id, type, hint, title, description) => {
  const html = interpolateString(template, {
    'type': type,
    'id': id,
    'hint': hint,
    'title': title,
    'description': linkifyText(description),
  });
  
  const doc = parseHTMLFromString(html, true);
  return container.appendChild(doc[0]);
}

/**
 * collectEntityData
 * @desc Method that retrieves all relevant <script type="application/json" /> and <template/> elements with
 *       its data-owner attribute pointing to the entity selector
 * @return {object} An object describing the data collected
 * 
 */
const collectEntityData = () => {
  const output = {
    templates: { },
    datasets: { },
  };

  const templates = document.querySelectorAll('template[data-owner="entity-selector"]');
  for (let i = 0; i < templates.length; ++i) {
    let template = templates[i];
    output.templates[template.getAttribute('name')] = Array.prototype.reduce.call(
      template.content.childNodes,
      (result, node) => result + (node.outerHTML || node.nodeValue),
      ''
    );
  }

  const datasets = document.querySelectorAll('script[type="application/json"][data-owner="entity-selector"]');
  for (let i = 0; i < datasets.length; ++i) {
    let datapoint = datasets[i];
    let parsed;
    try {
      parsed = JSON.parse(datapoint.innerText.trim());
    }
    catch (e) {
      parsed = [];
    }

    output.datasets[datapoint.getAttribute('name')] = parsed;
  }

  return output;
}

/**
 * initialiseSelector
 * @desc initialises the selector form, creates the initial entity cards and handles user interaction
 * @param {object} formData the associated form data
 * 
 */
const initialiseSelector = (formData) => {
  const { templates, datasets } = formData;
  const groupContainer = document.querySelector('#group-container');

  const entities = datasets?.data?.entities;
  if (!isNullOrUndefined(entities)) {
    const entityLen = entities.length;
    for (let i = 0; i < entityLen; ++i) {
      let entity = entities[i];
      const available = datasets?.data?.templates.filter(item => item.entity_class__id == entity.id);
      if (available.length < 1) {
        continue;
      }
      
      let group = createGroup(
        groupContainer,
        templates?.group,
        entityLen,
        entity.id,
        entity.name,
        entity.description
      );

      let childContainer = group.querySelector('#entity-options');
      for (let i = 0; i < available.length; ++i) {
        let item = available[i];
        let card = createCard(
          childContainer,
          templates?.card,
          item.id,
          'Template',
          `Version ${item.template_version}`,
          item.name,
          item.description
        );
    
        let btn = card.querySelector('#select-btn');
        btn.addEventListener('click', (e) => {
          window.location.href = strictSanitiseString(`${getCurrentURL()}${item.id}`);
        });
      }
    }
  }
}

/**
 * Main thread
 * @desc initialises the component once the dom is ready
 * 
 */
domReady.finally(() => {
  const formData = collectEntityData();
  initialiseSelector(formData);
});
