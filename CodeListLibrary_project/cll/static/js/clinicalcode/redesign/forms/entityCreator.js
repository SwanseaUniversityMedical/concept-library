import Tagify from "../components/tagify.js";
import PublicationCreator from "./clinical/publicationCreator.js";
import ConceptCreator from "./clinical/conceptCreator.js";

/**
 * ENTITY_OPTIONS
 * @desc Defines the ID for the form submission and save draft button(s)
 */
const ENTITY_OPTIONS = {
  // Whether to prompt that the form has been modified when the user tries to leave
  promptUnsaved: true,
};

/**
 * ENTITY_DATEPICKER_FORMAT
 * @desc Defines how the creator should format dates when producing form values
 */
const ENTITY_DATEPICKER_FORMAT = 'YYYY-MM-DD';

/**
 * ENTITY_FORM_BUTTONS
 * @desc Defines the ID for the form submission and save draft button(s)
 */
const ENTITY_FORM_BUTTONS = {
  'save': 'save-entity-btn',
  'submit': 'submit-entity-btn',
};

/**
 * ENTITY_HANDLERS
 * @desc Map of methods to initialise JS-driven components for the form
 *       as described by their data-class attribute
 */
const ENTITY_HANDLERS = {
  // Generates a tagify component for an element
  'tagify': (element) => {
    const data = element.parentNode.querySelectorAll(`data[for="${element.getAttribute('data-field')}"]`);
    
    let value = [];
    let options = [];
    for (let i = 0; i < data.length; ++i) {
      const datafield = data[i];
      const type = datafield.getAttribute('data-type')
      if (!datafield.innerText.trim().length) {
        continue;
      }

      try {
        switch (type) {
          case 'options': {
            options = JSON.parse(datafield.innerText);
          } break;

          case 'value': {
            value = JSON.parse(datafield.innerText);
          } break;
        }
      }
      catch(e) {
        console.warn(`Unable to parse datafield for Tagify element with target field: ${datafield.getAttribute('for')}`);
      }
    }

    const tagbox = new Tagify(element, {
      'autocomplete': true,
      'useValue': true,
      'allowDuplicates': false,
      'restricted': true,
      'items': options,
    });

    for (let i = 0; i < value.length; ++i) {
      const item = value[i];
      if (typeof item !== 'object' || !item.hasOwnProperty('name') || !item.hasOwnProperty('value')) {
        continue;
      }

      tagbox.addTag(item.name, item.value);
    }

    return tagbox;
  },

  // Generates a datepicker (single or range) component for an element
  'datepicker': (element) => {
    const range = element.getAttribute('data-range');
    const datepicker = new Lightpick({
      field: element,
      singleDate: range != 'true',
      selectForward: true,
      maxDate: moment(),
      onSelect: (start, end) => {
        if (isNullOrUndefined(start)) {
          return;
        }
    
        if (!start.isValid()) {
          return;
        }

        if (range == 'true') {
          if (isNullOrUndefined(end)) {
            return;
          }
      
          if (!end.isValid()) {
            return;
          }

          element.setAttribute('data-value', [start.format(ENTITY_DATEPICKER_FORMAT), end.format(ENTITY_DATEPICKER_FORMAT)].join(','));
          return;
        }
        element.setAttribute('data-value', start.format(ENTITY_DATEPICKER_FORMAT));
      },
    });

    let value = element.getAttribute('data-value');
    if (range == 'true') {
      value = value.split(/[\.\,\-]/)
                  .map(date => moment(date.trim(), ['DD-MM-YYYY', 'MM-DD-YYYY']))
                  .filter(date => date.isValid())
                  .slice(0, 2)
                  .sort((a, b) => -a.diff(b))
                  .map(date => date.format(ENTITY_DATEPICKER_FORMAT));
      
      const [start, end] = value;
      datepicker.setDateRange(end, start, true);
    } else {
      value = moment(value, ['DD-MM-YYYY', 'MM-DD-YYYY']);
      value = value.isValid() ? value : moment();
      value = value.format(ENTITY_DATEPICKER_FORMAT);
      datepicker.setDate(value, true);
    }

    return datepicker;
  },

  // Generates a markdown editor component for an element
  'md-editor': (element) => {
    const toolbar = element.parentNode.querySelector(`div[for="${element.getAttribute('data-field')}"]`);
    const data = element.parentNode.querySelector(`data[for="${element.getAttribute('data-field')}"]`);

    let value = data.innerText;
    if (isStringEmpty(value) || isStringWhitespace(value)) {
      value = ' ';
    }

    const mde = new TinyMDE.Editor({
      element: element,
      content: value
    });

    const bar = new TinyMDE.CommandBar({
      element: toolbar,
      editor: mde
    });

    element.addEventListener('click', () => {
      mde.e.focus();
    });

    return {
      editor: mde,
      toolbar: bar,
    };
  },

  // Generates a clinical publication list component for an element
  'clinical-publication': (element) => {
    const data = element.parentNode.querySelector(`data[for="${element.getAttribute('data-field')}"]`);
    
    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch {
      parsed = [];
    }

    return new PublicationCreator(element, parsed)
  },

  // Generates a clinical concept component for an element
  'clinical-concept': (element) => {
    const data = element.querySelector(`data[for="${element.getAttribute('data-field')}"]`);
    
  },
};

/**
 * collectFormData
 * @desc Method that retrieves all relevant <data/> elements with
 *       its data-owner attribute pointing to the entity creator.
 * @return {object} An object describing the data, with each key representing
 *                  the name of the <data/> element
 */
const collectFormData = () => {
  const values = document.querySelectorAll('data[data-owner="entity-creator"]');

  const result = { };
  for (let i = 0; i < values.length; ++i) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('type');

    let value = data.innerText;
    switch (type) {
      case 'text/array':
      case 'text/json': {
        value = JSON.parse(value);
      } break;

      case 'int': {
        value = parseInt(value);
      } break;
    }

    result[name] = value;
  }

  return result;
}

/**
 * getTemplateFields
 * @desc Attempts to retrieve the template's definition fields
 * @param {object} template The template object as provided by context
 * @return {object} The template's fields
 */
const getTemplateFields = (template) => {
  return template?.definition?.fields;
}

/**
 * createFormHandler
 * @desc Attempts to retrieve the template's definition fields
 * @param {node} element The node associated with this handler
 * @param {string} cls The data-class attribute value of that particular element
 * @return {object} An interface to control the behaviour of the component
 */
const createFormHandler = (element, cls) => {
  if (!ENTITY_HANDLERS.hasOwnProperty(cls)) {
    return;
  }

  return ENTITY_HANDLERS[cls](element);
}

/**
 * EntityCreator
 * @desc A class that can be used to control forms for templated dynamic content
 * 
 */
class EntityCreator {
  constructor(data, options) {
    this.data = data;
    this.formChanged = false;

    this.#buildOptions(options || { });
    this.#collectForm();
    this.#setUpForm();
    this.#setUpSubmission();
  }

  /**
   * getData
   * @returns {object} the template, metadata, any assoc. entity and the form method
   */
  getData() {
    return this.data;
  }

  /**
   * getForm
   * @returns {object} form describing the key/value pair of the form as defined
   *                   by its template
   */
  getForm() {
    return this.form;
  }

  /**
   * getFormButtons
   * @returns {object} returns the assoc. buttons i.e. save as draft, submit button
   */
  getFormButtons() {
    return this.buttons;
  }

  /**
   * getOptions
   * @returns {object} the parameters used to build this form
   */
  getOptions() {
    return this.options;
  }

  /**
   * isDirty
   * @returns whether the form has been modified and its data is now dirty
   */
  isDirty() {
    return this.formChanged;
  }

  /**
   * submitForm
   * @returns submits the form to create/update an entity
   */
  submitForm() {
    
  }

  /**
   * saveForm
   * @returns submits the form to save as a draft
   */
  saveForm() {
    
  }

  // Private methods
  #buildOptions(options) {
    this.options = mergeObjects(options, ENTITY_OPTIONS);
  }

  #collectForm() {
    const fields = getTemplateFields(this.data.template);
    if (!fields) {
      return console.error('Unable to initialise, no template fields passed');
    }
    
    const form = { };
    for (let field in fields) {
      const element = document.querySelector(`[data-field="${field}"`);
      if (!element) {
        continue;
      }

      form[field] = {
        element: element,
        validation: this.#getFieldValidation(field),
        value: this.#getFieldInitialValue(field),
      };
    }

    this.form = form;
  }

  #setUpForm() {
    for (let field in this.form) {
      const pkg = this.form[field];
      const cls = pkg.element.getAttribute('data-class');
      if (!cls) {
        continue;
      }

      this.form[field].handler = createFormHandler(pkg.element, cls);
    }

    if (this.options.promptUnsaved) {
      window.addEventListener('beforeunload', this.#handleOnLeaving.bind(this), { capture: true });
    }
  }

  #setUpSubmission() {
    this.formButtons = { }

    const submitBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['submit']}`);
    if (submitBtn) {
      submitBtn.addEventListener('click', this.submitForm.bind(this));
    }

    const saveBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['save']}`);
    if (saveBtn) {
      saveBtn.addEventListener('click', this.saveForm.bind(this));
    }
  }

  #handleOnLeaving(e) {
    if (this.isDirty()) {
      e.preventDefault();
      return e.returnValue = '';
    }
  }

  #getFieldValidation(field) {
    const fields = getTemplateFields(this.data.template);
    const packet = fields[field];
    if (packet?.is_base_field) {
      let metadata = this.data?.metadata;
      if (!metadata) {
        return null;
      }
      
      return metadata[field]?.validation;
    }

    return packet?.validation;
  }

  #getFieldInitialValue(field) {
    const entity = this.data?.entity;
    if (!entity) {
      return;
    }

    if (entity.hasOwnProperty(field)) {
      return entity[field];
    }

    if (!entity?.template_data.hasOwnProperty(field)) {
      return;
    }
    
    return entity.template_data[field];
  }
}

// Form initialisation
domReady.finally(() => {
  const data = collectFormData();

  window.entityForm = new EntityCreator(data, {
    promptUnsaved: false,
  });
});
