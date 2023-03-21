import { parse as parseCSV } from '../../vendor/csv.min.js';

/**
 * tryCleanCodingCSV
 * @desc Attempts to clean a coding CSV such that:
 *          1. leading and trailing null/empty rows are removed
 *          2. separates the first row as a header and the rest as data
 * 
 * @param {array[array[string]]} csv the CSV result array
 * @returns {object} that describes {header: [], data: []}
 */
const tryCleanCodingCSV = (csv) => {
  csv = csv.reduce((filtered, row) => {
    let testRow = row.filter(val => !isNullOrUndefined(val) && !isStringEmpty(val));
    if (testRow.length > 0) {
      filtered.push(testRow);
    }

    return filtered;
  }, []);

  if (csv.length < 2) {
    return { };
  }

  return {
    'header': csv[0],
    'data': csv.slice(1)
  }
}

/**
 * tryCleanCodingRow
 * @desc Attempts to clean a cell, given its col and row, such that:
 *         1. Only returns the first two values of a row - i.e. code & desc
 *         2. Removes leading and trailing whitespace
 * @param {str} val the cell value
 * @param {int} row the row index
 * @param {int} col the col index
 * @returns {str} the value if required
 */
const tryCleanCodingItem = (val, row, col) => {
  if (col > 2) {
    return;
  }
  
  return val.replace(/^\s+|\s+$/gm,'');
}

/**
  * tryParseCodingCSVFile
  * @desc Attempts to parse a file, as returned by an file input element as a CSV.
  * 
  *       The wrapped promise returned does NOT catch errors - it is expected
  *       that exceptions are handled by the caller
  * 
  * @param {object} file The file object as returned by a file input element
  * @returns {promise} A promise that resolves an 2D array, with each outer index 
  *                    representing a row of the CSV's values, and the inner index
  *                    representing a column
  */
const tryParseCodingCSVFile = (file) => {
  return new Promise((resolve, reject) => {
    let fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = reject;
    fr.readAsText(file, 'UTF-8');
  })
  .then(content => parseCSV(content, {typed: false}, (val, row, col) => tryCleanCodingItem(val, row, col)))
  .then(csv => tryCleanCodingCSV(csv))
}

/**
 * ConceptCreator
 * @desc A class that can be used to control concept creation
 * 
 */
export default class ConceptCreator {
  constructor(element, data) {
    this.data = data || [ ];
    this.element = element;
    this.state = {
      editing: false,
      data: null,
    };

    this.#collectTemplates();
    this.#setUp();
  }

  // Getters
  getData() {
    return this.data;
  }

  tryPromptUpload() {
    return new Promise((resolve, reject) => {
      tryOpenFileDialogue({
        allowMultiple: false,
        extensions: ['.csv', '.tsv'],
        callback: (selected, files) => {
          if (!selected) {
            return;
          }
  
          const file = files[0];
          tryParseCodingCSVFile(file)
            .then(res => resolve(res))
            .catch(e => reject);
        }
      });
    })
  }

  // Initialisation
  #collectTemplates() {
    this.templates = { };
    
    const templates = this.element.querySelectorAll('template');
    for (let i = 0; i < templates.length; ++i) {
      let template = templates[i];
      this.templates[template.getAttribute('id')] = Array.prototype.reduce.call(
        template.content.childNodes,
        (result, node) => result + (node.outerHTML || node.nodeValue),
        ''
      );
    }
  }

  #setUp() {
    for (let i = 0; i < this.data.length; ++i) {
      const concept = this.data[i];
      this.#tryRenderConceptComponent(concept);
    }
  }

  // Renderables
  #tryRenderConceptComponent(concept) {
    const template = this.templates['concept-item'];
    const html = interpolateHTML(template, {
      'concept_name': concept?.details?.name,
      'concept_id': concept?.concept_id,
      'concept_history_id': concept?.concept_history_id,
      'coding_id': concept?.coding_system?.id,
      'coding_system': concept?.coding_system?.description,
    });

    const containerList = this.element.querySelector('#concept-content-list');
    const doc = parseHTMLFromString(html);
    const conceptItem = containerList.appendChild(doc.body.children[0]);
    const headerButtons = conceptItem.querySelectorAll('#concept-accordian-header span[role="button"]');
    for (let i = 0; i < headerButtons.length; ++i) {
      headerButtons[i].addEventListener('click', this.#handleConceptHeaderButton.bind(this));
    }
  }

  // Handlers
  #toggleConcept(target) {
    const parent = target.parentNode
    parent.classList.toggle('is-open');

    if (parent.contains('is-open')) {
      // Render codelist
    }

    // Hide codelist

  }

  #handleConceptHeaderButton(e) {
    const target = e.target;
    const method = target.getAttribute('data-target');
    switch (method) {
      case 'is-open': {
        this.#toggleConcept(target);
      } break;

      case 'edit': {

      } break;
      
      case 'delete': {

      } break;

      default: break;
    }
  }
}
