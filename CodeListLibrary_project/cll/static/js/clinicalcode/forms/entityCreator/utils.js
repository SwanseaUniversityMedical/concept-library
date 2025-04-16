import Tagify from '../../components/tagify.js';
import ConceptCreator from '../clinical/conceptCreator.js';
import GroupedEnum from '../../components/groupedEnumSelector.js';
import ListEnum from '../../components/listEnumSelector.js';
import DoubleRangeSlider from '../../components/doubleRangeSlider.js';
import ContactListCreator from '../clinical/contactListCreator.js';
import PublicationCreator from '../clinical/publicationCreator.js';
import TrialCreator from '../clinical/trialCreator.js';
import EndorsementCreator from '../clinical/endorsementCreator.js';
import ReferenceCreator from '../clinical/referenceCreator.js';
import StringInputListCreator from '../stringInputListCreator.js';
import UrlReferenceListCreator from '../generic/urlReferenceListCreator.js';
import OntologySelectionService from '../generic/ontologySelector/index.js';
import VariableCreator from '../generic/variableCreator.js';
import IndicatorCalculationCreator from '../generic/indicatorCalculationCreator.js';

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
  // Generates a doublerangeslider component context
  'doublerangeslider': (element) => {
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

    return new DoubleRangeSlider(element, packet);
  },

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

  // Generates a listenum component context
  'listenum': (element) => {
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
        console.warn(`Unable to parse datafield for ListEnum element with target field: ${datafield.getAttribute('for')}`);
      }
    }

    return new ListEnum(element, packet);
  },

  // Generates a tagify component for an element
  'tagify': (element, dataset) => {
    const parent = element.parentElement;
    const data = parent.querySelectorAll(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);

    let varyDataVis = parseInt(element.getAttribute('data-vis') ?? '0');
    varyDataVis = !Number.isNaN(varyDataVis) && Boolean(varyDataVis);

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
      'onLoad': (box) => {
        for (let i = 0; i < value.length; ++i) {
          const item = value[i];
          if (typeof item !== 'object' || !item.hasOwnProperty('name') || !item.hasOwnProperty('value')) {
            continue;
          }

          box.addTag(item.name, item.value);
        }

        return () => {
          if (!varyDataVis) {
            return;
          }

          const choices = box?.options?.items?.length ?? 0;
          if (choices < 1) {
            parent.style.setProperty('display', 'none');
          }
        }
      }
    }, dataset);

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
      .slice(0, 2);

    if (value.every(x => x.isValid())) {
      value = value.sort((a, b) => a.diff(b));
    }

    const [start, end] = value.map(x => x.isValid() ? x.format('YYYY-MM-DD') : undefined);
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
    const data = element.parentNode.querySelector(`script[for="${element.getAttribute('data-field')}"]`);
    const value = data?.innerText;

    const mde = new EasyMDE({
      // Elem
      element: element,
      maxHeight: '300px',
      minHeight: '200px',

      // Behaviour
      autofocus: false,
      forceSync: false,
      autosave: { enabled: false },
      placeholder: 'Enter content here...',
      promptURLs: false,
      spellChecker: false,
      lineWrapping: true,
      unorderedListStyle: '-',
      renderingConfig: {
        singleLineBreaks: false,
        codeSyntaxHighlighting: false,
        sanitizerFunction: (renderedHTML) => strictSanitiseString(renderedHTML, { html: true }),
      },

      // Controls
      status: ['lines', 'words', 'cursor'],
      tabSize: 2,
      toolbar: [
        'heading', 'bold', 'italic', 'strikethrough', '|',
        'unordered-list', 'ordered-list', 'code', 'quote', '|',
        'link', 'image', 'table', '|',
        'preview', 'guide',
      ],
      toolbarTips: true,
      toolbarButtonClassPrefix: 'mde',
    });

    if (!isStringEmpty(value) && !isStringWhitespace(value)) {
      mde.value(value);
    }

    return {
      editor: mde,
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

  // Generates a list component for an element
  'url_list': (element) => {
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new UrlReferenceListCreator(element, parsed)
  },

  'contact-list': (element) => {
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);
    
    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new ContactListCreator(element, parsed)
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
  'clinical-trial': (element) => {
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);

    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new TrialCreator(element, parsed)
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

  'clinical-references':(element) => {
    const data = element.parentNode.querySelector(`script[type="application/json"][for="${element.getAttribute('data-field')}"]`);

    let parsed;
    try {
      parsed = JSON.parse(data.innerText);
    }
    catch (e) {
      parsed = [];
    }

    return new ReferenceCreator(element, parsed)

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
  },

  // HDRN-related
  'var_array': (element) => {
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
        console.warn(`Failed to parse validation measures attr "${datatype}" data:`, e)
      }
    }

    return new VariableCreator(element, data);
  },

  'indicator_calculation': (element) => {
    const nodes = element.querySelectorAll(`script[for="${element.getAttribute('data-field')}"]`);

    const data = { };
    for (let i = 0; i < nodes.length; ++i) {
      let node = nodes[i];

      const datatype = node.getAttribute('type');
      const dataname = node.getAttribute('data-name');
      if (isStringEmpty(datatype) || isStringEmpty(dataname)) {
        continue;
      }

      let innerText = node.innerText;
      if (isStringEmpty(innerText) || isStringWhitespace(innerText)) {
        continue;
      }

      try {
        if (datatype === 'application/json') {
          innerText = JSON.parse(innerText);
        }
        data[dataname] = innerText;
      }
      catch (e) {
        console.warn(`Failed to parse indicator calculations attr "${datatype}" data:`, e)
      }
    }

    return new IndicatorCalculationCreator(element, data);
  },
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
    const value = strictSanitiseString(element.value);
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

    const validation = packet?.validation;
    const dateClosureOptional = typeof validation === 'object' && validation?.closure_optional;

    const startValid = startDateInput.checkValidity(),
          endValid   = endDateInput.checkValidity();

    const meetsCriteria = (startValid && endValid) || (dateClosureOptional && (startValid || endValid));
    let value;
    if (meetsCriteria) {
      let dates = [moment(startDateInput.value, ['YYYY-MM-DD']), moment(endDateInput.value, ['YYYY-MM-DD'])]
      dates = dates.sort((a, b) => a.diff(b))

      const count = dates.reduce((filtered, x) => x.isValid() ? ++filtered : filtered, 0);
      switch (count) {
        case 1: {
          if (dateClosureOptional) {
            const [ startDate, endDate ] = dates.map(date => date.isValid() ? date.format(ENTITY_DATEPICKER_FORMAT) : '');
            value = `${startDate} - ${endDate}`;
          }
        } break;

        case 2: {
          const  [ startDate, endDate ] = dates.map(date => date.format(ENTITY_DATEPICKER_FORMAT));
          value = `${startDate} - ${endDate}`;
        } break;

        default:
          break;
      }
    }

    if (isMandatoryField(packet) && (!meetsCriteria || isNullOrUndefined(value) || isStringEmpty(value))) {
      return {
        valid: false,
        value: value,
        message: (isNullOrUndefined(value) || isStringEmpty(value)) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
      };
    } else if (isNullOrUndefined(value) || isStringEmpty(value)) {
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

  // Retrieves and validates groupedenum components
  'doublerangeslider': (field, packet) => {
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

  // Retrieves and validates groupedenum components
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

  // Retrieves and validates listenum compoonents
  'listenum': (field, packet) => {
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

  // Retrieves and validates list components
  'url_list': (field, packet) => {
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

  // Retrieves and validates contact list components
  'contact-list': (field, packet) => {
    const handler = packet.handler;
    const contacts = handler.getData();

    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(contacts) || contacts.length < 1) {
        return {
          valid: false,
          value: contacts,
          message: (isNullOrUndefined(contacts) || contacts.length < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, contacts);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: contacts,
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

  'clinical-trial': (field, packet) => {
    const handler = packet.handler;
    const trials = handler.getData();

    if (isMandatoryField(packet)) {
      if (isNullOrUndefined(trials) || trials.length < 1) {
        return {
          valid: false,
          value: trials,
          message: (isNullOrUndefined(trials) || trials.length < 1) ? ENTITY_TEXT_PROMPTS.REQUIRED_FIELD : ENTITY_TEXT_PROMPTS.INVALID_FIELD
        }
      }
    }

    const parsedValue = parseAsFieldType(packet, trials);
    if (!parsedValue || !parsedValue?.success) {
      return {
        valid: false,
        value: trials,
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

  'clinical-references': (field, packet) => {
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

    let value = handler.editor.value();
    value = typeof value === 'string' ? strictSanitiseString(value) : '';

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
  },

  // HDRN-related
  'var_array': (field, packet) => {
    const handler = packet.handler;
    const data = handler.getData();
    if (isMandatoryField(packet) && (!isObjectType(data) || Object.values(data).length < 1)) {
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

  'indicator_calculation': (field, packet) => {
    const handler = packet.handler;

    let values = { },
        length = 0;
    Object.entries(handler.elements).forEach(([role, editor]) => {
      const content = editor.value();

      values[role] = typeof content === 'string' ? strictSanitiseString(content) : '';
      if (!stringHasChars(values[role])) {
        values[role] = '';
      }

      length += values[role].length;
    });

    if (length === 0) {
      values = null;
    }

    return {
      valid: true,
      value: values,
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
export const createFormHandler = (element, cls, data, validation = undefined) => {
  if (!ENTITY_HANDLERS.hasOwnProperty(cls)) {
    return;
  }

  return ENTITY_HANDLERS[cls](element, data, validation);
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
 * resolveRangeOpts
 * @desc resolves the range assoc. with some component's properties (if available)
 * 
 * @param {string}              type             the name of the type assoc. with this range
 * @param {Record<string, any>} opts             the properties assoc. with the component containing this value/range
 * @param {boolean}             [forceStep=true] optionally specify whether to resolve a step interval regardless of range availability; defaults to `true`
 * 
 * @returns {Record<string, Record<string, string|number>>} the range values (if applicable)
 */
export const resolveRangeOpts = (type, opts, forceStep = true) => {
  let fmin = null;
  let fmax = null;
  let fstep = null;
  if (isObjectType(opts)) {
    fmin = typeof opts.min === 'number' ? opts.min : null;
    fmax = typeof opts.max === 'number' ? opts.max : null;
    fstep = typeof opts.step === 'number' ? opts.step : null;
  } else if (Array.isArray(opts) && opts.length >= 2) {
    fmin = typeof opts[0] === 'number' ? opts[0] : null;
    fmax = typeof opts[1] === 'number' ? opts[1] : null;
    fstep = null;
  }

  if (typeof fmin == 'number' && typeof fmax === 'number') {
    let tmp = Math.max(fmin, fmax);
    fmin = Math.min(fmin, fmax);
    fmax = tmp;
  }

  if (fstep === null && forceStep) {
    fstep = type.startsWith('int') ? 1 : 0.001;
  }

  return {
    hasStep: fstep !== null,
    hasRange: fmin !== null && fmax !== null,
    attr: {
      min: fmin !== null ? `min="${fmin}"` : '',
      max: fmax !== null ? `max="${fmax}"` : '',
      step: fstep !== null ? `step="${fstep}"` : '',
    },
    values: {
      min: fmin,
      max: fmax,
      step: fstep,
    },
  };
}

/**
 * parseAsFieldType
 * @desc parses the field as its type, returns true if no validation or type field
 * @param {object} packet the field data
 * @param {*} value the value retrieved from the form
 * @returns {object} that returns the success state of the parsing & the parsed value, if applicable
 */
export const parseAsFieldType = (packet, value, modifier) => {
  const validation = packet?.validation;
  if (isNullOrUndefined(validation)) {
    return {
      success: true,
      value: value
    }
  }

  let type = validation?.type;
  if (isObjectType(modifier) && modifier?.type) {
    type = modifier.type;
  }

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
      if (typeof value === 'string') {
        value = parseInt(value.trim());
      }

      if (typeof value === 'number') {
        value = Math.trunc(value);
        valid = !isNaN(value) && Number.isFinite(value) && Number.isSafeInteger(value);

        const range = resolveRangeOpts('int', validation?.range || validation?.properties?.range);
        if (valid && range.hasRange) {
          value = clampNumber(value, range.values.min, range.values.max);
        }
      } else {
        valid = false;
      }
    } break;

    case 'int_range': {
      if (isObjectType(value)) {
        let { min, max } = value;
        if (typeof min === 'number' && typeof max === 'number') {
          min = Math.min(min, max);
          max = Math.max(min, max);

          const range = resolveRangeOpts('int', validation?.range || validation?.properties?.range);
          if (valid && range.hasRange) {
            value = clampNumber(value, range.values.min, range.values.max);
          }

          value = { min: Math.trunc(min), max: Math.trunc(max) };
          break;
        }

        valid = false;
      } else if (!isNullOrUndefined(value)) {
        const output = [];
        if (typeof value === 'string') {
          value = value.trim().split(',');
        } else if (typeof value === 'number') {
          value = [value];
        }

        if (!Array.isArray(value)) {
          return false;
        }

        for (let i = 0; i < value.length; ++i) {
          let item = value[i];
          if (typeof item === 'string') {
            item = parseInt(item.trim());
          }

          if (typeof item !== 'number') {
            continue;
          }

          item = Math.trunc(item);
          valid = !isNaN(item) && Number.isFinite(item) && Number.isSafeInteger(item);

          if (!valid) {
            break;
          }

          output.push(item);
        }
        value = output;

        if (value.length === 1 && validation?.closure_optional) {
          const num = Math.trunc(value.shift());
          valid = !isNaN(num) && Number.isFinite(num) && Number.isSafeInteger(num);
          value = [num];
        } else if (value.length < 2 && !validation?.closure_optional) {
          valid = false;
        } else {
          const lower = Math.min(value[0], value[1]);
          const upper = Math.max(value[0], value[1]);
          value[0] = lower;
          value[1] = upper;
        }

        const range = resolveRangeOpts('int', validation?.range || validation?.properties?.range);
        if (valid && range.hasRange) {
          value[0] = clampNumber(value[0], range.values.min, range.values.max);
          value[1] = clampNumber(value[1], range.values.min, range.values.max);
        }
      }
    } break;

    case 'int_array': {
      const output = [];
      if (typeof value === 'string') {
        value = value.trim().split(',');
      } else if (typeof value === 'number') {
        value = [value];
      }

      if (!Array.isArray(value)) {
        break;
      }

      for (let i = 0; i < value.length; ++i) {
        let item = value[i];
        if (typeof item === 'string') {
          item = parseInt(item.trim());
        }
  
        if (typeof item !== 'number') {
          continue;
        }

        item = Math.trunc(item);
        valid = !isNaN(item) && Number.isFinite(item) && Number.isSafeInteger(item);

        if (!valid) {
          break;
        }
        output.push(item);
      }

      if (!valid) {
        break;
      }
      value = output;
    } break;

    case 'float':
    case 'decimal':
    case 'numeric': {
      if (typeof value === 'string') {
        const matches = value.trim().match(/(\+|-)?(((\d{1,3}([,?\d{3}])*(\.\d+)?)|(\d{1,}))|(\.\d{0,}))/m);
        if (!isNullOrUndefined(matches)) {
          value = parseFloat(matches.shift().trim().replaceAll(/,/g, ''));
        }
      }

      if (typeof value === 'number') {
        valid = !isNaN(value) && Number.isFinite(value);

        const range = resolveRangeOpts(type, validation?.range || validation?.properties?.range);
        if (valid && range.hasRange) {
          value = clampNumber(value, range.values.min, range.values.max);
        }
      } else {
        valid = false;
      }
    } break;

    case 'float_range':
    case 'decimal_range':
    case 'numeric_range': {
      if (isObjectType(value)) {
        let { min, max } = value;
        if (typeof min === 'number' && typeof max === 'number') {
          min = Math.min(min, max);
          max = Math.max(min, max);

          const range = resolveRangeOpts(type, validation?.range || validation?.properties?.range);
          if (valid && range.hasRange) {
            min = clampNumber(min, range.values.min, range.values.max);
            max = clampNumber(max, range.values.min, range.values.max);
          }

          value = { min, max };
          break;
        }
      } else {
        const output = [];
        if (typeof value === 'string') {
          value = value.trim().split(',');
        } else if (typeof value === 'number') {
          value = [value];
        }
  
        if (!Array.isArray(value)) {
          return false;
        }
  
        for (let i = 0; i < value.length; ++i) {
          let item = value[i];
          if (typeof item === 'string') {
            const matches = item.trim().match(/(\+|-)?(((\d{1,3}([,?\d{3}])*(\.\d+)?)|(\d{1,}))|(\.\d{0,}))/m);
            if (isNullOrUndefined(matches)) {
              valid = false;
              break;
            }
  
            item = parseFloat(matches.shift().trim());
          }
  
          if (typeof item !== 'number') {
            continue;
          }
  
          valid = !isNaN(item) && Number.isFinite(item);
  
          if (!valid) {
            break;
          }
  
          output.push(item);
        }
        value = output;
  
        if (value.length === 1 && validation?.closure_optional) {
          const num = value.shift();
          valid = !isNaN(num) && Number.isFinite(num);
          value = [num];
        } else if (value.length < 2 && !validation?.closure_optional) {
          valid = false;
        } else {
          const lower = Math.min(value[0], value[1]);
          const upper = Math.max(value[0], value[1]);
          value[0] = lower;
          value[1] = upper;
        }

        const range = resolveRangeOpts(type, validation?.range || validation?.properties?.range);
        if (valid && range.hasRange) {
          value[0] = clampNumber(value[0], range.values.min, range.values.max);
          value[1] = clampNumber(value[1], range.values.min, range.values.max);
        }
      }
    } break;

    case 'float_array':
    case 'decimal_array':
    case 'numeric_array': {
      const output = [];
      if (typeof value === 'string') {
        value = value.trim().split(',');
      } else if (typeof value === 'number') {
        value = [value];
      }

      if (!Array.isArray(value)) {
        break;
      }

      for (let i = 0; i < value.length; ++i) {
        let item = value[i];
        if (typeof item === 'string') {
          const matches = item.trim().match(/(\+|-)?(((\d{1,3}([,?\d{3}])*(\.\d+)?)|(\d{1,}))|(\.\d{0,}))/m);
          if (isNullOrUndefined(matches)) {
            valid = false;
            break;
          }

          item = parseFloat(matches.shift().trim());
        }

        if (typeof item !== 'number') {
          continue;
        }

        valid = !isNaN(item) && Number.isFinite(item);

        if (!valid) {
          break;
        }

        output.push(item);
      }

      if (!valid) {
        break;
      }
      value = output;
    } break;

    case 'percentage': {
      if (typeof value === 'string') {
        const matches = value.trim().match(/(\+|-)?(((\d{1,3}([,?\d{3}])*(\.\d+)?)|(\d{1,}))|(\.\d{0,}))(%)?/m);
        if (!isNullOrUndefined(matches)) {
          value = parseFloat(matches.shift().trim());

          let coercion = (isObjectType(modifier) && !isNullOrUndefined(modifier?.coercion))
            ? modifier.coercion
            : null;

          if (isNullOrUndefined(coercion)) {
            coercion = validation?.coercion;
          }

          const hasPercentageSymbol = !isNullOrUndefined(matches) ? (matches[matches.length - 1] === '%') : false;
          if (coercion === 'normalised' && hasPercentageSymbol) {
            value /= 100;
          } else if (coercion === 'percentage' && !hasPercentageSymbol) {
            value *= 100;
          }
        }
      }

      if (typeof value === 'number') {
        valid = !isNaN(value) && Number.isFinite(value);

        const range = resolveRangeOpts(type, validation?.range || validation?.properties?.range);
        if (valid && range.hasRange) {
          value = clampNumber(value, range.values.min, range.values.max);
        }
      } else {
        valid = false;
      }
    } break;

    case 'percentage_range': {
      if (isObjectType(value)) {
        let { min, max } = value;
        if (typeof min === 'number' && typeof max === 'number') {
          min = Math.min(min, max);
          max = Math.max(min, max);

          const range = resolveRangeOpts(type, validation?.range || validation?.properties?.range);
          if (valid && range.hasRange) {
            min = clampNumber(min, range.values.min, range.values.max);
            max = clampNumber(max, range.values.min, range.values.max);
          }

          value = { min, max };
          break;
        }
      } else {
        const output = [];
        if (typeof value === 'string') {
          value = value.trim().split(',');
        } else if (typeof value === 'number') {
          value = [value];
        }

        if (!Array.isArray(value)) {
          break;
        }

        for (let i = 0; i < value.length; ++i) {
          let item = value[i];
          if (typeof item === 'string') {
            const matches = item.trim().match(/(\+|-)?(((\d{1,3}([,?\d{3}])*(\.\d+)?)|(\d{1,}))|(\.\d{0,}))(%)?/m);
            if (!isNullOrUndefined(matches)) {
              item = parseFloat(matches.shift().trim());
    
              let coercion = (isObjectType(modifier) && !isNullOrUndefined(modifier?.coercion))
                ? modifier.coercion
                : null;

              if (isNullOrUndefined(coercion)) {
                coercion = validation?.coercion;
              }

              const hasPercentageSymbol = !isNullOrUndefined(matches) ? (matches[matches.length - 1] === '%') : false;
              if (coercion === 'normalised' && hasPercentageSymbol) {
                item /= 100;
              } else if (coercion === 'percentage' && !hasPercentageSymbol) {
                item *= 100;
              }
            }
          }

          if (typeof item !== 'number') {
            continue;
          }

          valid = !isNaN(item) && Number.isFinite(item);
          if (!valid) {
            break;
          }

          output.push(item);
        }

        if (!valid) {
          break;
        }
        value = output;

        const range = resolveRangeOpts(type, validation?.range || validation?.properties?.range);
        if (valid && range.hasRange) {
          value[0] = clampNumber(value[0], range.values.min, range.values.max);
          value[1] = clampNumber(value[1], range.values.min, range.values.max);
        }
      }
    } break;

    case 'ci_interval': {
      if (!isObjectType(value)) {
        valid = false;
        break;
      }

      const output = { };
      for (const key in value) {
        let item = value[key];
        if (key === 'probability') {
          item = parseAsFieldType({ validation: { type: 'percentage', range: [0, 100] }}, item);
          if (!item || !item?.success) {
            valid = false;
            break;
          }

          item = item.value;
        } else {
          let attemptCoercion;
          if (typeof item === 'string') {
            attemptCoercion = item.match(/^(\+|-)?(((\d{1,3}([,?\d{3}])*(\.?\d+)?)|(\d{1,}))|(\.\d+)?)(%)?$/m);
            attemptCoercion = !isNullOrUndefined(attemptCoercion);
          } else if (typeof item === 'number') {
            attemptCoercion = true;
          }

          let failure = false;
          if (attemptCoercion) {
            const res = parseAsFieldType({ validation: { type: 'float' } }, item);
            if (res && res?.success) {
              item = res.value;
            } else {
              failure = true;
            }
          }

          if (!failure && typeof item !== 'number' && typeof item !== 'string') {
            valid = false;
            break;
          }

          if (typeof item === 'number' && (isNaN(item) || !Number.isFinite(item))) {
            valid = false;
            break;
          }

          if (failure && typeof item === 'number') {
            item = item.toString();
          }

          if (typeof item === 'string' && !stringHasChars(item)) {
            valid = false;
            break;
          }
        }

        output[key] = item;
      }

      if (!valid) {
        break;
      }

      value = output;
    } break;

    case 'string': {
      value = !isNullOrUndefined(value) ? String(value) : null;

      const pattern = validation?.regex;
      if (!isNullOrUndefined(pattern)) {
        try {
          if (typeof pattern === 'string') {
            valid = new RegExp(pattern).test(value);
          } else if (Array.isArray(pattern)) {
            let test = undefined, i = 0;
            while (i < pattern.length) {
              test = pattern[i];
              if (typeof test !== 'string') {
                continue;
              }
  
              valid = new RegExp(test).test(value);
              if (valid) {
                break;
              }
            }
          }
        }
        catch (e) {
          console.error(`Failed to test String<value: ${value}> with err: ${e}`);
          valid = false;
        }

        if (!valid) {
          break;
        }
      }

      const { clippable, validateLen } = isObjectType(validation.properties) ? validation.properties : {};
      if (clippable || validateLen) {
        let len = validation?.['length'] || validation?.properties?.['length'];
        if (Array.isArray(len)) {
          len = len.length >= 2 ? len.slice(0, 2) : len?.[0];
        }
  
        if (Array.isArray(len)) {
          len = len.map(x => Math.floor(x));
  
          let min = Math.min(...len);
          let max = Math.max(...len);
          if (min === max) {
            len = min;
          } else {
            if (clippable) {
              value = value.substring(0, Math.min(value.length, max));
            } else if (validateLen && (value.length < min || value.length > max)) {
              value = { len: value.length };
              valid = false;
            }
          }
  
          if (!valid) {
            break;
          }
        }
  
        if (typeof len === 'number') {
          len = Math.floor(len);
  
          if (clippable) {
            value = value.substring(0, Math.min(value.length, len));
          } else if (validateLen && value.length > len) {
            value = { len: value.length };
            valid = false;
          }
  
          if (!valid) {
            break;
          }
        }
      }
    } break;

    case 'string_array': {
      if (!Array.isArray(value)) {
        valid = false;
        break;
      }

      value = value.map(item => String(item));
    } break;

    case 'publication': {
      if (!Array.isArray(value)) {
        valid = false;
      }
    } break;

    case 'organisation': {
      if (!isNullOrUndefined(value) && typeof value !== 'string' && typeof value !== 'number') {
        valid = false;
        break;
      }

      if (typeof value === 'string') {
        value = parseInt(value.trim());
      }

      if (typeof value === 'number') {
        value = Math.trunc(value);
        valid = !isNaN(value) && Number.isFinite(value) && Number.isSafeInteger(value);
      } else if (!isNullOrUndefined(value)) {
        valid = false;
      }
    } break;

    case 'var_array': {
      if (!isObjectType(value)) {
        valid = false;
        break;
      }

      const options = isObjectType(validation.options) ? validation.options : null;
      const properties = isObjectType(validation.properties) ? validation.properties : null;

      const allowUnknown = !!properties ? properties.allow_unknown : false;
      const allowDescription = !!properties ? properties.allow_description : false;

      const output = {};
      for (const key in value) {
        let item = value[key];
        if (!isObjectType(item)) {
          valid = false;
          break;
        }

        let description = null;
        if (allowDescription) {
          if (!isNullOrUndefined(item?.description) && typeof item?.description !== 'string') {
            item.description = String(item?.description);
          }

          if (typeof item.description === 'string') {
            description = item.description;
          }

          if (!stringHasChars(description)) {
            delete item.description;
          }
        }

        let success = false;
        if (options) {
          const props = options[key];
          if (!isNullOrUndefined(props)) {
            const res = parseAsFieldType(packet, item.value, props);
            if (!res || !res?.success) {
              valid = false;
              break
            }

            item = {
              name: typeof props.name === 'string' ? props.name : key,
              type: props.type,
              value: res.value,
              description: description,
            };
            success = true;
          }
        }

        if (!success && !allowUnknown) {
          valid = false;
          break;
        }

        if (!success) {
          const vtype = typeof item.type === 'string' && stringHasChars(item.type) ? item.type : null;
          const vlabel = typeof item.name === 'string' && stringHasChars(item.name) ? item.name : null;
          if (!vtype || !vlabel) {
            valid = false;
            break
          }

          const res = parseAsFieldType({ validation: { type: vtype }}, item.value);
          if (!res || !res?.success) {
            valid = false;
            break
          }

          item = {
            name: vlabel,
            type: vtype,
            value: res.value,
            description: description,
          };
        }

        if (item.hasOwnProperty('description') && (!allowDescription || item.description === null)) {
          delete item.description;
        }

        output[key] = item;
      }

      if (!valid) {
        break;
      }
      value = output;
    } break;

    case 'contacts':
    case 'publication': {
      if (!Array.isArray(value)) {
        valid = false;
      }
    } break;

    default:
      valid = true;
      break;
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
  const group = tryGetRootElement(packet.element, '.detailed-input-group');
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
