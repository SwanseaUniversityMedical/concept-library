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

domReady.finally(() => {
  initStepsWizard();

  const data = collectFormData();
  

});