import Tagify from '../../components/tagify.js';
import ConceptCreator from '../clinical/conceptCreator.js';
import GroupedEnum from '../../components/groupedEnumSelector.js';
import PublicationCreator from '../clinical/publicationCreator.js';
import EndorsementCreator from '../clinical/endorsementCreator.js';
import StringInputListCreator from '../stringInputListCreator.js';
import OntologySelectionService from '../generic/ontologySelector/index.js';

import {
  ENTITY_DATEPICKER_FORMAT,
  ENTITY_ACCEPTABLE_DATE_FORMAT,
  ENTITY_TEXT_PROMPTS
} from '../entityFormConstants.js';


/**
 * ENTITY_HANDLERS
 * @desc Map of methods to initialise JS-driven components for the form
 *       as described by their data-class attribute
 * 
 */
export const ENTITY_HANDLERS = {
  // Generates a groupedenum component context
  'groupedenum': (element) => {
    const data = element.parentNode.querySelectorAll(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
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
    const data = element.parentNode.querySelectorAll(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
    let value = [];
    let options = [];
    for (let i = 0; i < data.length; ++i) {
      const datafield = data[i];
      const type = datafield.getAttribute('desc-type');
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
      console.log(datepicker)
    }

    return datepicker;
  },

  // Generates a markdown editor component for an element
  'md-editor': (element) => {
    const toolbar = element.parentNode.querySelector(`div[for="${element.getAttribute('data-field')}"]`);
    const data = element.parentNode.querySelector(`data[for="${element.getAttribute('data-field')}"]`);

    let value = data?.innerHTML;
    if (!isStringEmpty(value) && !isStringWhitespace(value)) {
      value = convertMarkdownData(data)
    } else {
      value = '';
    }

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
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
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
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new PublicationCreator(element, parsed)
  },

  'clinical-endorsement':(element) => {
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new EndorsementCreator(element, parsed)

  },

  // Generates a clinical concept component for an element
  'clinical-concept': (element, dataset) => {
    const data = element.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);

    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new ConceptCreator(element, dataset, parsed);
  },

  // Generates an ontology selection component for an element
  'ontology': (element, dataset) => {
    const nodes = element.querySelectorAll(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);

    const data = { };
    for (let i = 0; i < nodes.length; ++i) {
      let node = nodes[i];

      const datatype = node.getAttribute('data-type');
      if (isStringEmpty(datatype)) {
        continue;
      }

      let innerText = node.innerText;
      if (isStringEmpty(innerText) || isStringWhitespace(innerText)) {
        continue;
      }

      try {
        innerText = JSON.parse(innerText);
        data[datatype] = innerText;
      }
      catch (e) {
        console.warn('Failed to parse Ontology data:', e)
      }
    }

    return new OntologySelectionService(element, dataset, data);
  }
};

/**
 * ENTITY_FIELD_COLLECTOR
 * @desc a map that describes how each component, described by its
 *       data-class, should be read from to derive the field's data
 * 
 * @return {object} that describes { valid: bool, value: *, message: string|null }
 */
export const ENTITY_FIELD_COLLECTOR = {
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

  'clinical-endorsement': (field, packet) => {
    const handler = packet.handler;
    const endorsements = handler.getData();

    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(endorsements) || endorsements.length < 1) {
        return {
          valid: false,
          value: endorsements,
          message: (isNullOrUndefined(endorsements) || endorsements.length < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, endorsements);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: endorsements,
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

  // Generates an ontology selection component for an element
  'ontology': (field, packet) => {
    const handler = packet.handler;
    const data = handler.getValue(true);
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
  }
};

/**
 * collectFormData
 * @desc Method that retrieves all relevant <script type="application/json" /> elements with
 *       its data-owner attribute pointing to the entity creator.
 * @return {object} An object describing the data, with each key representing
 *                  the name of the <script type="application/json" /> element
 */
export const collectFormData = () => {
  const values = document.querySelectorAll('script[type="application/json"][data-owner="entity-creator"]');

  // collect the form data
  const result = { };
  for (let i = 0; i < values.length; ++i) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('desc-type');

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
export const getTemplateFields = (template) => {
  return template?.definition?.fields;
}

/**
 * createFormHandler
 * @desc Attempts to retrieve the template's definition fields
 * @param {node} element The node associated with this handler
 * @param {string} cls The data-class attribute value of that particular element
 * @return {object} An interface to control the behaviour of the component
 */
export const createFormHandler = (element, cls, data) => {
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
export const isMandatoryField = (packet) => {
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
export const parseAsFieldType = (packet, value) => {
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
export const tryGetFieldTitle = (field, packet) => {
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
