import Tagify from "../components/tagify.js";

const ENTITY_DATEPICKER_FORMAT = 'YYYY-MM-DD';

const ENTITY_HANDLERS = {
  'tagify': (element) => {
    const data = element.parentNode.querySelectorAll(`data[for="${element.getAttribute('data-field')}"]`);
    
    let value = [];
    let options = [];
    for (let i = 0; i < data.length; ++i) {
      const datafield = data[i];
      const type = datafield.getAttribute('data-type')
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
      'useValue': false,
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
  'datepicker': (element) => {
    const range = element.getAttribute('data-range');
    const datepicker = new Lightpick({
      field: element,
      singleDate: range != 'true',
      selectForward: true,
      maxDate: moment()
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

    return {
      editor: mde,
      toolbar: bar,
    };
  },
  'publication-list': (element) => {

  },
}

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

const getTemplateFields = (template) => {
  return template?.definition?.fields;
}

const createFormHandler = (element, cls) => {
  if (!ENTITY_HANDLERS.hasOwnProperty(cls)) {
    return;
  }

  return ENTITY_HANDLERS[cls](element);
}

class EntityCreator {
  constructor(data) {
    this.data = data;

    this.#collectForm();
    this.#setUpForm();
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

domReady.finally(() => {
  const data = collectFormData();
  const creator = new EntityCreator(data);

});
