import { stickifyTable } from "../components/tables.js";

const updateTrackerStyle = (navbar, trackers, headerOffset) => {
  for (let i = 0; i < trackers.length; i++) {
    const tracker = trackers[i];
    const offset = tracker.getBoundingClientRect().y - navbar.getBoundingClientRect().y + headerOffset;
    const size = tracker.offsetHeight;

    let progress = 0;
    if (offset < 0) {
      progress = Math.min((Math.abs(offset) / (size - (size/1.25))) * 100, 100);
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

domReady.finally(() => {
  initStepsWizard();
  
  // Stickify codelist table(s)
  const tables = document.querySelectorAll('#codelist-concept-table');
  Object.values(tables).forEach(e => stickifyTable(e));

  // 
});

