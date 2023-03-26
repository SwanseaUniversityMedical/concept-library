import Tagify from '../components/tagify.js';
import PublicationCreator from './clinical/publicationCreator.js';
import ConceptCreator from './clinical/conceptCreator.js';

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
  'cancel': 'cancel-entity-btn',
  'submit': 'submit-entity-btn',
};

/**
 * ENTITY_HANDLERS
 * @desc Map of methods to initialise JS-driven components for the form
 *       as described by their data-class attribute
 * 
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
    catch (e) {
      parsed = [];
    }

    return new PublicationCreator(element, parsed)
  },

  // Generates a clinical concept component for an element
  'clinical-concept': (element, dataset) => {
    const data = element.querySelector(`data[for="${element.getAttribute('data-field')}"]`);

    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new ConceptCreator(element, dataset?.template, parsed)
  },
};

/**
 * ENTITY_FIELD_COLLECTOR
 * @desc a map that describes how each component, described by its
 *       data-class, should be read from to derive the field's data
 * 
 * @return {object} that describes { valid: bool, value: *, message: string|null }
 */
const ENTITY_FIELD_COLLECTOR = {
  // Retrieves and validates text inputbox components
  'inputbox': (field, packet) => {
    const element = packet.element;
    const value = element.value;
    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(value) || isStringEmpty(value)) {
        return {
          valid: false,
          value: value,
          message: `${field} field is required`
        }
      }
    }

    if (isNullOrUndefined(value) || !element.checkValidity()) {
      return {
        valid: true,
        value: null,
      }
    }

    const parsedValue = parseAsFieldType(packet, value);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: value,
        message: `${field} field is invalid`
      }
    }

    return {
      valid: true,
      value: parsedValue?.value.trim()
    }
  },

  // Retrieves and validates dropdown components
  'dropdown': (field, packet) => {
    const element = packet.element;
    const selected = element.options[element.selectedIndex];
    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(selected) || element.selectedIndex < 0) {
        return {
          valid: false,
          value: selected.value,
          message: `${field} field is required`
        }
      }
    }
    
    if (isNullOrUndefined(selected) || !element.checkValidity()) {
      return {
        valid: true,
        value: null
      }
    }
    
    const parsedValue = parseAsFieldType(packet, selected.value);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: selected.value,
        message: `${field} field is invalid`
      }
    }

    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates radiobutton components
  'radiobutton': (field, packet) => {
    const element = packet.element;
    
    let selected;
    for (let i = 0; i < element.children.length; ++i) {
      const option = element.children[i];
      if (option.nodeName != 'INPUT') {
        continue;
      }

      if (!option.checked) {
        continue;
      }

      selected = option;
      break;
    }

    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(selected)) {
        return {
          valid: false,
          value: selected,
          message: `${field} field is required`
        }
      }
    }
    
    if (isNullOrUndefined(selected) || !element.checkValidity()) {
      return {
        valid: true,
        value: null
      }
    }

    const dataValue = selected.getAttribute('data-value');
    const parsedValue = parseAsFieldType(packet, dataValue);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: dataValue,
        message: `${field} field is invalid`
      }
    }
    
    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates datepicker components
  'datepicker': (field, packet) => {
    const element = packet.element;
    const value = element.value;
    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(value) || isStringEmpty(value)) {
        return {
          valid: false,
          value: value,
          message: `${field} field is required`
        }
      }
    }

    if (isNullOrUndefined(value) || isStringEmpty(value)) {
      return {
        valid: true,
        value: null,
      }
    }

    const parsedValue = parseAsFieldType(packet, value);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: value,
        message: `${field} field is invalid`
      }
    }

    return {
      valid: true,
      value: parsedValue?.value
    }
  },
  
  // Retrieves and validates group select components (internally they are radiobuttons)
  'group-select': (field, packet) => {
    const element = packet.element;
    
    let selected;
    for (let i = 0; i < element.children.length; ++i) {
      const option = element.children[i];
      if (option.nodeName != 'INPUT') {
        continue;
      }

      if (!option.checked) {
        continue;
      }

      selected = option;
      break;
    }

    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(selected)) {
        return {
          valid: false,
          value: selected,
          message: `${field} field is required`
        }
      }
    }

    if (isNullOrUndefined(selected) || !element.checkValidity()) {
      return {
        valid: true,
        value: null
      }
    }

    const dataValue = selected.getAttribute('data-value');
    const parsedValue = parseAsFieldType(packet, dataValue);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: dataValue,
        message: `${field} field is invalid`
      }
    }
    
    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates tagify components
  'tagify': (field, packet) => {
    const handler = packet.handler;
    const tags = handler.getActiveTags().map(item => item.value);
    
    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(tags) || tags.length < 1) {
        return {
          valid: false,
          value: tags,
          message: `${field} field is required`
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, tags);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: tags,
        message: `${field} field is invalid`
      }
    }
    
    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates publication components
  'clinical-publication': (field, packet) => {
    const handler = packet.handler;
    const publications = handler.getData();
    
    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(publications) || publications.length < 1) {
        return {
          valid: false,
          value: publications,
          message: `${field} field is required`
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, publications);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: publications,
        message: `${field} field is invalid`
      }
    }
    
    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates MDE components
  'md-editor': (field, packet) => {
    const handler = packet.handler;
    const value = handler.editor.getContent();
    
    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(value) || isStringEmpty(value)) {
        return {
          valid: false,
          value: value,
          message: `${field} field is required`
        }
      }
    }

    if (isNullOrUndefined(value)) {
      return {
        valid: true,
        value: null,
      }
    }

    const parsedValue = parseAsFieldType(packet, value);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: value,
        message: `${field} field is invalid`
      }
    }

    return {
      valid: true,
      value: parsedValue?.value.trim()
    }
  },

  // No validation required for concept as it's handled in the ConceptCreator
  'clinical-concept': (field, packet) => {
    const handler = packet.handler;
    return {
      valid: true,
      value: handler.getCleanedData()
    }
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
const createFormHandler = (element, cls, data) => {
  if (!ENTITY_HANDLERS.hasOwnProperty(cls)) {
    return;
  }

  return ENTITY_HANDLERS[cls](element, data);
}

/**
 * isMandatoryField
 * @desc given a field's packet, will determine whether it is mandatory or not
 * @param {object} packet the field data
 * @returns {boolean} that reflects whether the field is mandatory
 */
const isMandatoryField = (packet) => {
  const validation = packet?.validation;
  if (isNullOrUndefined(validation)) {
    return false;
  }

  return !isNullOrUndefined(validation?.mandatory) && validation.mandatory;
}

/**
 * parseAsFieldType
 * @desc parses the field as its type, returns true if no validation or type field
 * @param {object} packet the field data
 * @param {*} value the value retrieved from the form
 * @returns {object} that returns the success state of the parsing & the parsed value, if applicable
 */
const parseAsFieldType = (packet, value) => {
  const validation = packet?.validation;
  if (isNullOrUndefined(validation)) {
    return {
      success: true,
      value: value
    }
  }

  const type = validation?.type;
  if (isNullOrUndefined(type)) {
    return {
      success: true,
      value: value
    }
  }

  let valid = true;
  switch (type) {
    case 'enum': {
      value = parseInt(value);
      valid = !isNaN(value);
    } break;

    case 'int': {
      value = parseInt(value);
      valid = !isNaN(value);      
    } break;

    case 'string': {
      value = String(value);
      
      const pattern = validation?.regex;
      if (isNullOrUndefined(pattern)) {
        valid = true;
        break;
      }

      valid = new RegExp(pattern).test(value);
    } break;

    case 'string_array': {
      if (!Array.isArray(value)) {
        valid = false;
        break;
      }

      value = value.map(item => String(item));
    } break;

    case 'int_array': {
      if (!Array.isArray(value)) {
        valid = false;
        break;
      }

      const output = [ ];
      for (let i = 0; i < value.length; ++i) {
        const item = parseInt(value[i]);
        if (isNaN(item)) {
          valid = false;
          break;
        }
        output.push(item);
      }

      if (!valid) {
        break;
      }
      value = output;
    } break;
  }

  return {
    success: valid,
    value: value
  }
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

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getFormMethod
   * @desc describes whether the form is a create or an update form, where 1 = create & 2 = update
   * @returns {int} int representation of the form method enum
   */
  getFormMethod() {
    return this.data?.method;
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

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/  
  /**
   * makeDirty
   * @desc sets the form as dirty - used by child components
   * @returns this, for chaining
   */
  makeDirty() {
    this.formChanged = true;
    return this;
  }

  /**
   * submitForm
   * @desc submits the form to create/update an entity
   */
  submitForm() {
    const form = this.#collectFieldData();
    console.log(form);
  }

  /**
   * cancelForm
   * @desc Prompts the user to cancel the form if changes have been made and then either:
   *        a) redirects the user to the search page if the entity does not exist
   *          *OR*
   *        b) redirects the user to the detail page if the entity exists
   * 
   *      If no changes have been made, the user is immediately redirected
   */
  cancelForm() {
    if (!this.isDirty()) {
      this.#redirectFormClosure();
      return;
    }

    promptClientModal({
      title: 'Are you sure?',
      content: '<p>Are you sure you want to exit this form?</p>'
    })
    .then(() => {
      this.#redirectFormClosure();
    })
    .catch(() => { /* SINK */ });
  }

  /*************************************
   *                                   *
   *               Private             *
   *                                   *
   *************************************/
  /**
   * redirectFormClosure
   * @desc redirection after canellation or submission of a form
   * @param {object|null} reference optional parameter to redirect to newly created entity
   */
  #redirectFormClosure(reference = null) {
    
  }

  /**
   * collectFieldData
   * @desc iteratively collects the form data and validates it against the template data
   * @returns {object} which describes the form data and associated errors
   */
  #collectFieldData() {
    const data = { };
    const errors = [ ];
    for (const [field, packet] of Object.entries(this.form)) {
      if (!ENTITY_FIELD_COLLECTOR.hasOwnProperty(packet?.dataclass)) {
        continue;
      }

      // Collect the field value & validate it
      const result = ENTITY_FIELD_COLLECTOR[packet?.dataclass](field, packet);
      if (result && result?.valid) {
        data[field] = result.value;
        continue;
      }

      // Validation has failed, append the error message
      errors.push(result);
    }
    
    return {
      data: data,
      errors: errors,
    };
  }

  /**
   * buildOptions
   * @desc private method to merge the expected options with the passed options - passed takes priority
   * @param {dict} options the option parameter 
   */
  #buildOptions(options) {
    this.options = mergeObjects(options, ENTITY_OPTIONS);
  }

  /**
   * collectForm
   * @desc collects the form data associated with the template's fields
   */
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

  /**
   * getFieldValidation
   * @desc attempts to retrieve the validation data associated with a field, given by its template
   * @param {string} field 
   * @returns {object|null} a dict containing the validation information, if present
   */
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

  /**
   * getFieldInitialValue
   * @desc attempts to determine the initial value of a field based on the entity's template data
   * @param {string} field 
   * @returns {*} any field's initial value
   */
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


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * setUpForm
   * @desc Initialises the form by instantiating handlers for the components,
   *       renders any assoc. components, and responsible for handling the
   *       prompt when users leave the page with unsaved data
   */
  #setUpForm() {
    for (let field in this.form) {
      const pkg = this.form[field];
      const cls = pkg.element.getAttribute('data-class');
      if (!cls) {
        continue;
      }

      this.form[field].handler = createFormHandler(pkg.element, cls, this.data);
      this.form[field].dataclass = cls;
    }

    if (this.options.promptUnsaved) {
      window.addEventListener('beforeunload', this.#handleOnLeaving.bind(this), { capture: true });
    }
  }

  /**
   * setUpSubmission
   * @desc initialiser for the submit and cancel buttons associated with this form
   */
  #setUpSubmission() {
    this.formButtons = { }

    const submitBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['submit']}`);
    if (submitBtn) {
      submitBtn.addEventListener('click', this.submitForm.bind(this));
    }

    const cancelBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['cancel']}`);
    if (cancelBtn) {
      cancelBtn.addEventListener('click', this.cancelForm.bind(this));
    }
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleOnLeaving
   * @desc responsible for prompting the user to confirm if they want to leave without saving the page data
   * @param {event} e the associated event
   */
  #handleOnLeaving(e) {
    if (this.isDirty()) {
      e.preventDefault();
      return e.returnValue = '';
    }
  }
}

/**
 * Main thread
 * @desc initialises the form after collecting the assoc. form data
 */
domReady.finally(() => {
  const data = collectFormData();

  window.entityForm = new EntityCreator(data, {
    promptUnsaved: false,
  });
});
