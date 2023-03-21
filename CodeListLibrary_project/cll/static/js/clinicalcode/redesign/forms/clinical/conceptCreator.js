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

    // Test csv lib & utils
    const box = element.querySelector('#no-available-concepts');
    box.addEventListener('click', (e) => {
      tryOpenFileDialogue({
        allowMultiple: false,
        extensions: ['.csv', '.tsv'],
        callback: (selected, files) => {
          if (!selected) {
            return;
          }

          const file = files[0];
          tryParseCodingCSVFile(file)
            .then(res => console.log(res))
            .catch(e => console.warn(e));
        }
      });
    });
  }

  getData() {
    return this.data;
  }
}
