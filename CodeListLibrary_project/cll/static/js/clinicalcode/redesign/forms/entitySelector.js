/**
 * collectEntityData
 * @desc Method that retrieves all relevant <data/> and <template/> elements with
 *       its data-owner attribute pointing to the entity selector
 * @return {object} An object describing the data collected
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

  const datasets = document.querySelectorAll('data[data-owner="entity-selector"]');
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
 * createCard
 * @desc method to interpolate a card using a template
 * @param {node} container the container element
 * @param {string} template the template fragment
 * @param {*} id any data value
 * @param {*} type any data value
 * @param {*} hint any data value
 * @param {*} title any data value
 * @param {*} description any data value
 * @returns {node} the interpolated element after appending to the container node
 */
const createCard = (container, template, id, type, hint, title, description) => {
  const html = interpolateHTML(template, {
    'type': type,
    'id': id,
    'hint': hint,
    'title': title,
    'description': description,
  });
  
  const doc = parseHTMLFromString(html);
  return container.appendChild(doc.body.children[0]);
}

/**
 * redrawConfirmation
 * @desc toggles the disabled state of the 'next-btn' element
 * @param {object} currentOptions the current state of the selector
 */
const redrawConfirmation = (currentOptions) => {
  const { entity, template } = currentOptions;

  const continueButton = document.querySelector('#next-btn');
  continueButton.disabled = isNullOrUndefined(entity) || isNullOrUndefined(template);
}

/**
 * redrawTemplate
 * @desc redraws the template cards
 * @param {object} templates describes all the template fragments as returned by collectEntityData
 * @param {object} datasets describes all the dataset information as returned by collectEntityData
 * @param {object} currentOptions describes the current selector state
 */
const redrawTemplate = (templates, datasets, currentOptions) => {
  const templateOptions = document.querySelector('#entity-templates');
  const root = tryGetRootElement(templateOptions, 'entity-panel__group');
  templateOptions.innerHTML = '';

  const available = datasets?.data?.templates.filter(item => item.entity_class__id == currentOptions.entity)
  if (available.length < 1) {
    root.classList.add('hide');
    return;
  }
  
  for (let i = 0; i < available.length; ++i) {
    let item = available[i];
    let card = createCard(
      templateOptions,
      templates?.card,
      item.id,
      'Template',
      `Version ${item.template_version}`,
      item.name,
      item.description
    );

    let btn = card.querySelector('#select-btn');
    btn.addEventListener('click', (e) => {
      currentOptions.template = card.getAttribute('data-id');
      redrawConfirmation(currentOptions);
    });
  }
  root.classList.remove('hide');
}

/**
 * initialiseSelector
 * @desc initialises the selector form, creates the initial entity cards and handles user interaction
 * @param {*} formData 
 */
const initialiseSelector = (formData) => {
  const { templates, datasets } = formData;
  const continueButton = document.querySelector('#next-btn');
  const entityOptions = document.querySelector('#entity-options');

  const currentOptions = {
    entity: null,
    template: null,
  }

  const entities = datasets?.data?.entities;
  if (!isNullOrUndefined(entities)) {
    for (let i = 0; i < entities.length; ++i) {
      let entity = entities[i];
      let card = createCard(
        entityOptions,
        templates?.card,
        entity.id,
        'Entity',
        entity.entity_prefix,
        entity.name,
        entity.description
      );

      let btn = card.querySelector('#select-btn');
      btn.addEventListener('click', (e) => {
        currentOptions.entity = card.getAttribute('data-id');
        redrawTemplate(templates, datasets, currentOptions)
      });
    }
  }

  continueButton.addEventListener('click', (e) => {
    if (isNullOrUndefined(currentOptions?.entity) || isNullOrUndefined(currentOptions?.template)) {
      return;
    }

    window.location.href = `${getCurrentURL()}${currentOptions?.template}`;
  });
}

// Main
domReady.finally(() => {
  const formData = collectEntityData();
  initialiseSelector(formData);
});
