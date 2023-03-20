/**
 * ConceptCreator
 * @desc A class that can be used to control concept creation
 * 
 */

import { parse as parseCSV } from '../../vendor/csv.min.js';

export default class ConceptCreator {
  constructor(element, data) {
    this.data = data || [ ];

    // Test csv lib
    const box = element.querySelector('#no-available-concepts');
    box.addEventListener('click', (e) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.csv';

      input.addEventListener('change', (e) => {
        if (e.target.files.length < 1) {
          return;
        }

        const file = e.target.files[0];
        const reader = new Promise((resolve, reject) => {
          let fr = new FileReader()
          fr.onload = () => resolve(fr.result);
          fr.onerror = reject;
          fr.readAsText(file, 'UTF-8');
        })
        .then((content) => {
          let parsed;
          try {
            parsed = parseCSV(content);
          }
          catch (e) {
            console.warn(e);
          }
          finally {
            if (typeof parsed !== 'undefined') {
              console.log(parsed);
            }
          }
        })
        .catch(e => console.error(e));
      });

      input.click();
    });
  }

  getData() {
    return this.data;
  }
}
