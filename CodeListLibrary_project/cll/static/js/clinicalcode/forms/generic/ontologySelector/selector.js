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

    this.activeItem = componentData?.dataset?.[0];
    this.activeData = deepCopy(this?.activeItem?.nodes);

    this.#initialise();
  }


  /*************************************
   *                                   *
   *               Private             *
   *                                   *
   *************************************/
  async #fetchNodeData(id) {
    const src = this?.activeItem?.model?.source;
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

  #pushDataset(index) {
    const dataset = this.dataset?.[index];
    if (isNullOrUndefined(dataset)) {
      return;
    }
    this.activeItem = dataset;

    const data = this.activeData;
    data.splice(0, data.length);
    data.push(...dataset.nodes);
    this.treeComponent.reload();
  }


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  #initialise() {
    const component = eleTree({
      el: '#ontology-list',
      lazy: true,
      data: this.activeData,
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

    component.on('lazyload', this.#handleLoading.bind(this));
    component.on('checkbox', this.#handleCheckbox.bind(this));
  
    // Temp. debug
    document.addEventListener('keyup', (e) => {
      e.preventDefault();

      if (e.keyCode == 13) {
        const index = Math.floor(Math.random() * 3);
        this.#pushDataset(index)
      }
    });
  }


  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  #handleLoading(group) {
    const data = group.data;
    const load = group.load;

    this.#fetchNodeData(data.id)
      .then(node => load(node.children))
      .catch(console.error);
  }

  #handleCheckbox(group) {
    // Temp. debug
    console.log(this.treeComponent.getChecked());
  }
}
