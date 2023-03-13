import FuzzyQuery from "../components/fuzzyQuery.js";
import Tagify from "../components/tagify.js";
import { stickifyTable } from "../components/tables.js";

const updateTrackerStyle = (navbar, trackers, headerOffset) => {
  for (let i = 0; i < trackers.length; i++) {
    const tracker = trackers[i];
    const offset = tracker.getBoundingClientRect().y - navbar.getBoundingClientRect().y + headerOffset;
    const size = tracker.offsetHeight;

    let progress = 0;
    if (offset < 0) {
      progress = Math.min((Math.abs(offset) / (size - (size/4))) * 100, 100);
    }
    tracker.style.setProperty('--progress-percentage', `${progress}%`);
  }
}

const initStepsWizard = () => {
  document.querySelectorAll('.steps-wizard__item').forEach(elem => {
    elem.addEventListener('click', e => {
      const target = document.querySelector(`#${elem.getAttribute('data-target')}`);
      if (target) {
        window.scroll({ top: target.offsetTop, left: 0, behavior: 'smooth' });
      }
    });
  });
  
  const navbar = document.querySelector('.page-navigation');
  const header = document.querySelector('.main-header');
  const trackers = document.querySelectorAll('.phenotype-progress__item');
  document.addEventListener('scroll', e => {
    updateTrackerStyle(navbar, trackers, header ? header.getBoundingClientRect().y / 2 : 0);
  });
  updateTrackerStyle(navbar, trackers, header ? header.getBoundingClientRect().y / 2 : 0);
}

const collectFormData = () => {
  const values = document.querySelectorAll('data[data-owner="entity-creator"]');

  const result = { };
  for (let i = 0; i < values.length; ++i) {
    const data = values[i];
    const name = data.getAttribute('name');
    const type = data.getAttribute('type');

    let value = data.getAttribute('value');
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
  console.log(cls);
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

      this.form.handler = createFormHandler(pkg.element, cls);
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
    if (!entity || !entity?.definition.hasOwnProperty(field)) {
      return null;
    }
    
    return entity.definition[field];
  }
}

domReady.finally(() => {
  initStepsWizard();

  const data = collectFormData();
  const creator = new EntityCreator(data);

});