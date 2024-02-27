import * as Constants from './constants.js';

/**
 * OntologySelectionService
 * @desc Class that allows the selection of items from arbitrary
 *       directed acyclic graphs that define taggable ontologies
 * 
 */

export default class OntologySelectionService {
  constructor(element, phenotype, componentData, options) {
    this.value = componentData?.value;
    this.domain = getBrandedHost();
    this.options = mergeObjects(options || { }, Constants.OPTIONS);
    this.dataset = componentData?.dataset;
    this.element = element;
    this.phenotype = phenotype;
    this.activeDataset = componentData?.dataset?.[0];

    this.#initialise();
  }

  async #fetchNodeData(id) {
    const src = this?.activeDataset?.model?.source;
    if (isStringEmpty(src) || isStringWhitespace(src)) {
      throw new Error(`Expected valid string source, got ${typeof(src)}`); 
    }

    const url = interpolateString(
      Constants.ENDPOINTS.FETCH_NODE,
      { host: this.domain, source: src, id: id.toString() }
    );

    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
      throw new Error(`An error has occurred: ${response.status}`);
    }

    let res;
    try {
      res = await response.json();
    }
    catch (e) {
      throw new Error(`An error has occurred: ${e}`); 
    }

    return res;
  }

  #initialise() {
    const component = eleTree({
      el: '#ontology-list',
      lazy: true,
      data: this.activeDataset?.nodes,
      showCheckbox: true,
      highlightCurrent: true,
      icon: {
        checkFull: '.eletree_icon-check_full',
        checkHalf: '.eletree_icon-check_half',
        checkNone: '.eletree_icon-check_none',
        dropdownOff: '.eletree_icon-dropdown_right',
        dropdownOn: '.eletree_icon-dropdown_bottom',
        loading: '.eleTree-animate-rotate.eletree_icon-loading1',
      }
    });
    this.treeComponent = component;

    component.on('lazyload', (group) => {
      const data = group.data;
      const load = group.load;

      this.#fetchNodeData(data.id)
        .then(node => load(node.children))
        .catch(console.error);
    });
  }
}
