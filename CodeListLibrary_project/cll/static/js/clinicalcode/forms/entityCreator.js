import Tagify from '../components/tagify.js';
import StringInputListCreator from './stringInputListCreator.js';
import PublicationCreator from './clinical/publicationCreator.js';
import ConceptCreator from './clinical/conceptCreator.js';
import GroupedEnum from '../components/groupedEnumSelector.js';

/**
 * ENTITY_OPTIONS
 * @desc Defines the ID for the form submission and save draft button(s)
 */
const ENTITY_OPTIONS = {
  // Whether to prompt that the form has been modified when the user tries to leave
  promptUnsaved: true,
  // Whether to force toast errors instead of using the field group
  forceErrorToasts: false,
};

/**
 * ENTITY_DATEPICKER_FORMAT
 * @desc Defines how the creator should format dates when producing form values
 */
const ENTITY_DATEPICKER_FORMAT = 'YYYY/MM/DD';

/**
 * ENTITY_ACCEPTABLE_DATE_FORMAT
 * @desc Defines acceptable date formats
 */
const ENTITY_ACCEPTABLE_DATE_FORMAT = ['DD-MM-YYYY', 'MM-DD-YYYY', 'YYYY-MM-DD'];

/**
 * ENTITY_TOAST_MIN_DURATION
 * @desc the minimum message time for a toast notification
 */
const ENTITY_TOAST_MIN_DURATION = 5000; // ms, or 5s

/**
 * ENTITY_FORM_BUTTONS
 * @desc Defines the ID for the form submission and save draft button(s)
 */
const ENTITY_FORM_BUTTONS = {
  'cancel': 'cancel-entity-btn',
  'submit': 'submit-entity-btn',
};

/**
 * ENTITY_TEXT_PROMPTS
 * @desc any text that is used throughout the enjtity creator & presented to the user
 */
const ENTITY_TEXT_PROMPTS = {
  // Prompt when cancellation is requested and the data is dirty
  CANCEL_PROMPT: {
    title: 'Are you sure?',
    content: '<p>Are you sure you want to exit this form?</p>'
  },
  // Prompt when attempting to save changes to a legacy version
  HISTORICAL_PROMPT: {
    title: 'Are you sure?',
    content: `
      <p>
        <strong>
          You are saving a legacy Phenotype.
          Updating this Phenotype will overwrite the most recent version.
        </strong>
      </p>
      <p>Are you sure you want to do this?</p>
    `
  },
  // Informs user that they're trying to change group access to null when they've derived access
  DERIVED_GROUP_ACCESS: 'Unable to change group when you\'re deriving access from a group!',
  // Validation error when a field is null
  REQUIRED_FIELD: '${field} field is required, it cannot be empty',
  // Validation error when a field is empty
  INVALID_FIELD: '${field} field is invalid',
  // Message when form is invalid
  FORM_IS_INVALID: 'You need to fix the highlighted fields before saving',
  // Message when user attempts to POST without changing the form
  NO_FORM_CHANGES: 'You need to update the form before saving',
  // Message when POST submission fails due to server error
  SERVER_ERROR_MESSAGE: 'It looks like we couldn\'t save. Please try again',
  // Message when the API fails
  API_ERROR_INFORM: 'We can\'t seem to process your form. Please context an Admin',
  // Message when a user has failed to confirm / cancel an editable component before attemping to save
  CLOSE_EDITOR: 'Please close the ${field} editor first.'
}

/**
 * ENTITY_HANDLERS
 * @desc Map of methods to initialise JS-driven components for the form
 *       as described by their data-class attribute
 * 
 */
const ENTITY_HANDLERS = {
  // Generates a groupedenum component context
  'groupedenum': (element) => {
    const data = element.parentNode.querySelectorAll(`data[for="${element.getAttribute('data-field')}"]`);
    
    const packet = { };
    for (let i = 0; i < data.length; ++i) {
      let datafield = data[i];
      if (!datafield.innerText.trim().length) {
        continue;
      }

      let type = datafield.getAttribute('data-type');
      try {
        packet[type] = JSON.parse(datafield.innerText);
      }
      catch (e) {
        console.warn(`Unable to parse datafield for GroupedEnum element with target field: ${datafield.getAttribute('for')}`);
      }
    }

    return new GroupedEnum(element, packet);
  },

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

  // Handles data for daterange selectors
  'daterange': (element) => {
    const id = element.getAttribute('id');
    const startDateInput = element.querySelector(`#${id}-startdate`);
    const endDateInput = element.querySelector(`#${id}-enddate`);

    if (isNullOrUndefined(startDateInput) || isNullOrUndefined(endDateInput)) {
      return;
    }

    let value = element.getAttribute('data-value');
    if (isNullOrUndefined(value)) {
      return;
    }

    value = value.split(/[\.\,\-]/)
      .map(date => moment(date.trim(), ENTITY_ACCEPTABLE_DATE_FORMAT))
      .filter(date => date.isValid())
      .slice(0, 2)
      .sort((a, b) => a.diff(b))
      .map(date => date.format('YYYY-MM-DD'));

    const [start, end] = value;
    startDateInput.setAttribute('value', start);
    endDateInput.setAttribute('value', end);
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
                  .map(date => moment(date.trim(), ENTITY_ACCEPTABLE_DATE_FORMAT))
                  .filter(date => date.isValid())
                  .slice(0, 2)
                  .sort((a, b) => -a.diff(b))
                  .map(date => date.format('YYYY-MM-DD'));
      
      const [start, end] = value;
      datepicker.setDateRange(end, start, true);
    } else {
      value = moment(value, ENTITY_ACCEPTABLE_DATE_FORMAT);
      value = value.isValid() ? value : moment();
      value = value.format('YYYY-MM-DD');
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

  // Generates a list component for an element
  'string_inputlist': (element) => {
    const data = element.parentNode.querySelector(`data[for="${element.getAttribute('data-field')}"]`);
    
    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new StringInputListCreator(element, parsed)
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

    return new ConceptCreator(element, dataset, parsed);
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
          message: (isNullOrUndefined(value) || isStringEmpty(value)) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    if (isNullOrUndefined(value) || !element.checkValidity() || isStringEmpty(value)) {
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
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
      }
    }

    return {
      valid: true,
      value: typeof parsedValue?.value == 'string' ? parsedValue?.value.trim() : parsedValue?.value
    }
  },

  // Retrieves and validates dropdown components
  'dropdown': (field, packet) => {
    const element = packet.element;
    const selected = element.options[element.selectedIndex];
    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(selected) || element.selectedIndex < 1) {
        return {
          valid: false,
          value: selected.value,
          message: (isNullOrUndefined(selected) || element.selectedIndex < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
          message: (isNullOrUndefined(selected) || !element.checkValidity()) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
      }
    }
    
    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates daterange selector components
  'daterange': (field, packet) => {
    const element = packet.element;
    const id = element.getAttribute('id');
    const startDateInput = element.querySelector(`#${id}-startdate`);
    const endDateInput = element.querySelector(`#${id}-enddate`);

    let value;
    if (startDateInput.checkValidity() && endDateInput.checkValidity()) {
      let dates = [moment(startDateInput.value, ['YYYY-MM-DD']), moment(endDateInput.value, ['YYYY-MM-DD'])]
      dates = dates.sort((a, b) => a.diff(b))
                   .filter(date => date.isValid());

      if (dates.length === 2) {
        let [ startDate, endDate ] = dates.map(date => date.format(ENTITY_DATEPICKER_FORMAT));
        value = `${startDate} - ${endDate}`;
      }
    }
    
    if (isMandatoryField(packet)) {
      if (!startDateInput.checkValidity() || !endDateInput.checkValidity() || isNullOrUndefined(value) || isStringEmpty(value)) {
        return {
          valid: false,
          value: value,
          message: (isNullOrUndefined(value) || isStringEmpty(value)) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
          message: (isNullOrUndefined(value) || isStringEmpty(value)) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
      }
    }

    return {
      valid: true,
      value: parsedValue?.value
    }
  },
  
  // Retrieves and validates group select components (internally they are radiobuttons)
  'group-select': (field, packet, controller) => {
    const element = packet.element;

    let selected = element.options[element.selectedIndex];
    if (isMandatoryField(packet)) {
      if (!element.checkValidity() || isNullOrUndefined(selected) || element.selectedIndex < 0) {
        return {
          valid: false,
          value: !isNullOrUndefined(selected) ? selected.value : null,
          message: (isNullOrUndefined(selected) || element.selectedIndex < 0) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }
    
    if (isNullOrUndefined(selected)) {
      return {
        valid: true,
        value: controller.getSafeGroupId(),
      }
    }

    let parsedValue = parseAsFieldType(packet, selected.value);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: controller.getSafeGroupId(),
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
      }
    }

    return {
      valid: true,
      value: controller.getSafeGroupId(parsedValue?.value),
    }
  },

  // Retrieves and validates groupedenum compoonents
  'groupedenum': (field, packet) => {
    const handler = packet.handler;
    const value = handler.getValue();

    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(value)) {
        return {
          valid: false,
          value: value,
          message: ENTITY_TEXT_PROMPTS.REQUIRED_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, value);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: value,
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
          message: (isNullOrUndefined(tags) || tags.length < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, tags);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: tags,
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
      }
    }
    
    return {
      valid: true,
      value: parsedValue?.value
    }
  },

  // Retrieves and validates list components
  'string_inputlist': (field, packet) => {
    const handler = packet.handler;
    const listItems = handler.getData();

    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(listItems) || listItems.length < 1) {
        return {
          valid: false,
          value: listItems,
          message: (isNullOrUndefined(listItems) || listItems.length < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, listItems);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: listItems,
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
          message: (isNullOrUndefined(publications) || publications.length < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, publications);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: publications,
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
          message: (isNullOrUndefined(value) || isStringEmpty(value)) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
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
        message: ENTITY_TEXT_PROMPTS.INVALID_FIELD
      }
    }

    return {
      valid: true,
      value: parsedValue?.value.trim()
    }
  },

  // No validation required for concept as it's handled in the ConceptCreator
  // We only need to check length if mandatory
  'clinical-concept': (field, packet) => {
    const handler = packet.handler;
    const data = handler.getCleanedData();
    if (isMandatoryField(packet) && data.length < 1) {
      return {
        valid: false,
        value: data,
        message: ENTITY_TEXT_PROMPTS.REQUIRED_FIELD
      }
    }

    return {
      valid: true,
      value: data,
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

  // collect the form data
  const result = { };
  for (let i = 0; i < values.length; ++i) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('type');

    let value = data.innerText;
    if (!isNullOrUndefined(value) && !isStringEmpty(value.trim())) {
      switch (type) {
        case 'text/array':
        case 'text/json': {
          value = JSON.parse(value);
        } break;

        case 'int': {
          value = parseInt(value);
        } break;
      }
    }

    result[name] = value || { };

    const referral = data.getAttribute('referral-url');
    if (!isNullOrUndefined(referral)) {
      result[name].referralURL = referral;
    }
  }

  // merge metadata into template's fields for easy access
  if (result?.metadata && result?.template) {
    for (const [key, value] of Object.entries(result.metadata)) {
      result.template.definition.fields[key] = { is_base_field: true };
    }
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
    case 'int':
    case 'enum': {
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

    case 'publication': {
      if (!Array.isArray(value)) {
        valid = false;
      }
      break;
    }
  }

  return {
    success: valid,
    value: value
  }
}

/**
 * tryGetFieldTitle
 * @desc given a field and its template data, will attempt to find
 *       the associated title from its root element group.
 * 
 *       If not found, will transform its field name into a human 
 *       readable format.
 * @param {string} field the name of the field
 * @param {object} packet the field's associated template data
 * @return {string} the title of this field
 */
const tryGetFieldTitle = (field, packet) => {
  const group = tryGetRootElement(packet.element, 'detailed-input-group');
  const title = !isNullOrUndefined(group) ? group.querySelector('.detailed-input-group__title') : null;
  if (!isNullOrUndefined(title)) {
    return title.innerText.trim();
  }

  if (packet.handler && typeof packet.handler?.getTitle == 'function') {
    const handle = packet.handler.getTitle();
    if (handle) {
      return handle;
    }
  }

  return transformTitleCase(field.replace('_', ' '));
}

/**
 * EntityCreator
 * @desc A class that can be used to control forms for templated dynamic content
 * 
 */
class EntityCreator {
  #locked = false;

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
   * isLocked
   * @desc whether we're still awaiting the promise to resolve
   * @returns {boolean} represents status of promise
   */
  isLocked() {
    return this.#locked;
  }

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
   * @returns {boolean} whether the form has been modified and its data is now dirty
   */
  isDirty() {
    return this.data?.is_historical === 1 || this.formChanged;
  }

  /**
   * isEditingChildren
   * @desc checks whether the user is editing a child component
   * @returns {boolean} reflects editing state
   */
  isEditingChildren() {
    for (const [field, packet] of Object.entries(this.form)) {
      if (!packet.handler || !packet.handler.isInEditor) {
        continue;
      }

      if (packet.handler.isInEditor()) {
        return true;
      }
    }

    return false;
  }

  /**
   * getActiveEditor
   * @desc finds the active editor that the user is interacting with
   * @returns {object|null} the active component
   */
  getActiveEditor() {
    for (const [field, packet] of Object.entries(this.form)) {
      if (!packet.handler || !packet.handler.isInEditor) {
        continue;
      }

      if (packet.handler.isInEditor()) {
        return {
          field: field,
          packet: packet,
        };
      }
    }
  }

  /**
   * getSafeGroupId
   * @desc attempts to safely get the default group id if the 
   *       user attempts to change the group when they have derived
   *       access from another group
   * @param {integer|null} groupId optional parameter to test
   * @returns {integer|null} the safe group id
   */
  getSafeGroupId(groupId) {
    groupId = !isNullOrUndefined(groupId) && groupId >= 0 ? groupId : null;

    if (this.data?.derived_access !== 1) {
      return groupId;
    }

    if (isNullOrUndefined(groupId) || groupId < 0) {
      if (window.ToastFactory) {
        window.ToastFactory.push({
          type: 'error',
          message: ENTITY_TEXT_PROMPTS.DERIVED_GROUP_ACCESS,
          duration: ENTITY_TOAST_MIN_DURATION,
        });
      }

      return this.form?.group?.value;
    }

    return groupId;
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
    // Check that our children aren't in an editor state
    const child = this.getActiveEditor();
    if (child) {
      let title = tryGetFieldTitle(child.field, child.packet);
      title = title || child.field;

      return window.ToastFactory.push({
        type: 'warning',
        message: interpolateHTML(ENTITY_TEXT_PROMPTS.CLOSE_EDITOR, { field: title }),
        duration: ENTITY_TOAST_MIN_DURATION,
      });
    }

    // Clear prev. error messages
    this.#clearErrorMessages();

    // Collect form data & validate
    const { data, errors } = this.#collectFieldData();

    // If there are errors, update the assoc. fields & prompt the user
    if (errors.length > 0) {
      let minimumScrollY;
      for (let i = 0; i < errors.length; ++i) {
        const error = errors[i];
        const packet = this.form?.[error.field];
        if (isNullOrUndefined(packet)) {
          continue;
        }

        const elem = this.#displayError(packet, error);
        if (!isNullOrUndefined(elem)) {
          if (isNullOrUndefined(minimumScrollY) || elem.offsetTop < minimumScrollY) {
            minimumScrollY = elem.offsetTop;
          }
        }
      }

      minimumScrollY = !isNullOrUndefined(minimumScrollY) ? minimumScrollY : 0;
      window.scrollTo({ top: minimumScrollY, behavior: 'smooth' });
      
      return window.ToastFactory.push({
        type: 'danger',
        message: ENTITY_TEXT_PROMPTS.FORM_IS_INVALID,
        duration: ENTITY_TOAST_MIN_DURATION,
      });
    }

    // Peform dict diff to see if any changes, if not, inform the user to do so
    if (!this.isDirty() && !hasDeltaDiff(this.initialisedData, data)) {
      return window.ToastFactory.push({
        type: 'warning',
        message: ENTITY_TEXT_PROMPTS.NO_FORM_CHANGES,
        duration: ENTITY_TOAST_MIN_DURATION,
      });
    }

    // If no errors and it is different, then attempt to POST
    if (this.#locked) {
      return;
    }
    this.#locked = true;

    const spinner = startLoadingSpinner();
    try {
      const token = getCookie('csrftoken');
      const request = {
        method: 'POST',
        cache: 'no-cache',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'X-CSRFToken': token,
          'Authorization': `Bearer ${token}`
        },
        body: this.#generateSubmissionData(data),
      };
  
      fetch('', request)
        .then(response => {
          if (!response.ok) {
            return Promise.reject(response);
          }
          return response.json();
        })
        .then(content => {
          this.formChanged = false;
          this.initialisedData = data;
          return content;
        })
        .then(content => {
          this.#redirectFormClosure(content);
        })
        .catch(error => {
          if (typeof error.json === 'function') {
            this.#handleAPIError(error);
          } else {
            this.#handleServerError(error);
          }
          spinner.remove();
        })
        .finally(() => {
          this.#locked = false;
        });
    }
    catch (e){
      this.#locked = false;
      spinner.remove();
    }
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

    window.ModalFactory.create(ENTITY_TEXT_PROMPTS.CANCEL_PROMPT)
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
   * handleAPIError
   * @desc handles error responses from the POST request
   * @param {*} error the API error response
   */
  #handleAPIError(error) {
    error.json()
      .then(e => {
        const message = e?.message;
        if (!message) {
          this.#handleServerError(e);
        }

        const { type: errorType, errors } = message;
        console.error(`API Error<${errorType}> occurred:`, errors);

        window.ToastFactory.push({
          type: 'danger',
          message: ENTITY_TEXT_PROMPTS.API_ERROR_INFORM,
          duration: ENTITY_TOAST_MIN_DURATION,
        });
      })
      .catch(e => this.#handleServerError);
  }

  /**
   * handleServerError
   * @desc handles server errors when POSTing data
   * @param {*} error the server error response
   */
  #handleServerError(error) {
    if (error?.statusText) {
      console.error(error.statusText);
    } else {
      console.error(error);
    }
    
    window.ToastFactory.push({
      type: 'danger',
      message: ENTITY_TEXT_PROMPTS.SERVER_ERROR_MESSAGE,
      duration: ENTITY_TOAST_MIN_DURATION,
    });
  }

  /**
   * generateSubmissionData
   * @desc packages & jsonifies the form data for POST submission
   * @param {object} data the data we wish to submit
   * @returns {string} jsonified data packet
   */
  #generateSubmissionData(data) {
    // update the data with legacy fields (if still present in template)
    const templateData = this.data?.entity?.template_data;
    if (!isNullOrUndefined(templateData)) {
      const templateFields = getTemplateFields(this.data?.template);
      for (const [key, value] of Object.entries(templateData)) {
        if (data.hasOwnProperty(key) || !templateFields.hasOwnProperty(key)) {
          continue;
        }
        
        data[key] = value;
      }
    }
    
    // package the data
    const packet = {
      method: this.getFormMethod(),
      data: data,
    };

    if (this.data?.object) {
      const { id, history_id } = this.data.object;
      packet.entity = { id: id, version_id: history_id };
    }

    if (this.data?.template) {
      packet.template = {
        id: this.data.template.id,
        version: this.data.template?.definition?.template_details?.version
      }
    }

    return JSON.stringify(packet);
  }

  /**
   * redirectFormClosure
   * @desc redirection after canellation or submission of a form
   * @param {object|null} reference optional parameter to redirect to newly created entity
   */
  #redirectFormClosure(reference = null) {
    // Redirect to newly created object if available
    if (!isNullOrUndefined(reference)) {
      window.location.href = reference.redirect;
      return;
    }

    // Redirect to previous entity if available
    const object = this.data?.object;
    if (object?.referralURL) {
      window.location.href = object.referralURL;
      return;
    }

    // Redirect to search page
    window.location.href = this.data.links.referralURL;
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
      const result = ENTITY_FIELD_COLLECTOR[packet?.dataclass](field, packet, this);
      if (result && result?.valid) {
        data[field] = result.value;
        continue;
      }

      // Validation has failed, append the error message
      const title = tryGetFieldTitle(field, packet);
      result.field = field;
      result.message = interpolateHTML(result.message, { field: title });
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
      const element = document.querySelector(`[data-field="${field}"]`);
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
    // const fields = getTemplateFields(this.data.template);
    // const packet = fields[field];
    // if (packet?.is_base_field) {
    //   let metadata = this.data?.metadata;
    //   if (!metadata) {
    //     return null;
    //   }
      
    //   return metadata[field]?.validation;
    // }

    // // return packet?.validation;
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

    const { data, errors } = this.#collectFieldData();
    this.initialisedData = data;
  }

  /**
   * setUpSubmission
   * @desc initialiser for the submit and cancel buttons associated with this form
   */
  #setUpSubmission() {
    this.formButtons = { }

    const submitBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['submit']}`);
    if (submitBtn) {
      if (this.data?.is_historical === 1) {
        submitBtn.addEventListener('click', (e) => {
          window.ModalFactory.create(ENTITY_TEXT_PROMPTS.HISTORICAL_PROMPT)
            .then(() => {
              this.submitForm();
            })
            .catch(() => { /* SINK */ });
        })
      } else {
        submitBtn.addEventListener('click', this.submitForm.bind(this));
      }
    }

    const cancelBtn = document.querySelector(`#${ENTITY_FORM_BUTTONS['cancel']}`);
    if (cancelBtn) {
      cancelBtn.addEventListener('click', this.cancelForm.bind(this));
    }
  }

  /**
   * setAriaErrorLabels
   * @desc appends aria attributes to the element input field
   *       so that screen readers / accessibility tools are
   *       able to inform the user of the field error
   * @param {node} element the element to append aria attributes
   * @param {object} error the error object as generated by the validation method
   */
  #setAriaErrorLabels(element, error) {
    element.setAttribute('aria-invalid', true);
    element.setAttribute('aria-description', error.message);
  }

  /**
   * clearErrorMessages
   * @desc clears all error messages currently rendered within the input groups
   */
  #clearErrorMessages() {
    // Remove appended error messages
    const items = document.querySelectorAll('.detailed-input-group__error');
    for (let i = 0; i < items.length; ++i) {
      const item = items[i];
      item.remove();
    }

    for (const [field, packet] of Object.entries(this.form)) {
      // Remove aria labels
      const element = packet.element;
      element.setAttribute('aria-invalid', false);
      element.setAttribute('aria-description', null);

      // Remove component error messages
      if (!isNullOrUndefined(packet.handler) && typeof packet.handler?.clearErrorMessages == 'function') {
        packet.handler.clearErrorMessages();
      }
    }
  }

  /**
   * displayError
   * @desc displays the error packets for individual fields as generated by
   *       the field validation methods
   * @param {object} packet the field's template packet
   * @param {object} error the generated error object
   * @returns {node|null} returns the error element if applicable
   */
  #displayError(packet, error) {
    const element = packet.element;
    this.#setAriaErrorLabels(element, error);

    // Add __error class below title if available & the forceErrorToasts parameter was not passed
    if (!this.options.forceErrorToasts) {
      const inputGroup = tryGetRootElement(element, 'detailed-input-group');
      if (!isNullOrUndefined(inputGroup)) {
        const titleNode = inputGroup.querySelector('.detailed-input-group__title');
        const errorNode = createElement('p', {
          'aria-live': 'true',
          'className': 'detailed-input-group__error',
          'innerText': error.message,
        });

        titleNode.after(errorNode);
        return errorNode;
      }

      if (packet.handler && typeof packet.handler?.displayError == 'function') {
        return packet.handler.displayError(error);
      }
    }

    // Display error toast if no appropriate input group
    window.ToastFactory.push({
      type: 'danger',
      message: error.message,
      duration: ENTITY_TOAST_MIN_DURATION,
    });

    return null;
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
    if (this.#locked) {
      return;
    }
    
    const { data, errors } = this.#collectFieldData();
    if (this.isDirty() || hasDeltaDiff(this.initialisedData, data)) {
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
    promptUnsaved: true,
  });
});
