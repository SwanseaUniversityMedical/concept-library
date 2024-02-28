import * as Constants from './constants.js';
import OntologySelectionModal from './modal.js';

/**
 * OntologySelectionService
 * @desc Class that allows the selection of items from arbitrary
 *       directed acyclic graphs that define taggable ontologies
 * 
 */

export default class OntologySelectionService {
  static DataTarget = 'ontology-service';

  constructor(element, phenotype, componentData, options) {
    this.value = componentData?.value;
    this.domain = getBrandedHost();
    this.dataset = componentData?.dataset;
    this.element = element;
    this.phenotype = phenotype;

    this.#initialise(options);
  }


  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/

  /**
   * isOpen
   * @desc reflects whether the selection dialogue is currently open
   * @returns {boolean} whether the dialogue is open
   */
  isOpen() {
    return !!this.renderable;
  }


  /*************************************
   *                                   *
   *               Private             *
   *                                   *
   *************************************/

  /**
   * initialise
   * @desc Initialises the class by resolving its component templates,
   *       handles any data & event initialisation, incl. any rendering
   * @param {object|null} options optional parameters
   */
  #initialise(options) {
    this.options = mergeObjects(options || { }, Constants.OPTIONS);

    const button = this.element.querySelector('#add-input-btn');
    button.addEventListener('click', this.#handleAddButton.bind(this));

    const templates = { };
    const elements = this.element.querySelectorAll('template');
    for (let i = 0; i < elements.length; ++i) {
      let template = elements[i];
      let dataTarget = template.getAttribute('data-target');
      if (dataTarget !== OntologySelectionService.DataTarget) {
        continue;
      }

      let dataName = template.getAttribute('data-name');
      if (isStringEmpty(dataName) || isStringWhitespace(dataName)) {
        continue;
      }

      templates[dataName] = Array.prototype.reduce.call(
        template.content.childNodes,
        (result, node) => result + (node.outerHTML || node.nodeValue),
        ''
      );
    }
    this.templates = templates;

    // debug
    document.addEventListener('keyup', (e) => {
      if (e.keyCode !== 13) {
        return;
      }

      if (!this.isOpen()) {
        return;
      }

      const activeSource = this.activeItem?.model?.source;
      this.#pushDataset(activeSource === 0 ? 1 : 0);
    })
  }

  /**
   * fetchNodeData
   * @desc asynchronous method to fetch ontology related data via API
   * @param {int} id the id of the desired node
   * @returns {Promise<object|null>} the API response (if successful)
   */
  async #fetchNodeData(id) {
    const src = this?.activeItem?.model?.source;
    if (isNullOrUndefined(src) || typeof(src) !== 'number') {
      throw new Error(`Expected valid numerical source, got ${typeof(src)}`); 
    }

    const url = interpolateString(
      Constants.ENDPOINTS.FETCH_NODE,
      { host: this.domain, source: src.toString(), id: id.toString() }
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

  /**
   * pushDataset
   * @desc event to handle the changes required by eleTree
   * @param {int} index the source index of the desired dataset
   * 
   */
  #pushDataset(index) {
    if (!this.isOpen()) {
      return;
    }

    const dataset = this.dataset.find(e => e?.model?.source == index);
    if (isNullOrUndefined(dataset)) {
      return;
    }
    this.activeItem = dataset;

    const data = this.activeData;
    data.splice(0, data.length);
    data.push(...dataset.nodes);

    this.renderable?.reload();
  }


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/

  /**
   * showDialogue
   * @desc internal renderable handler to instantiate
   *       the selection modal
   * 
   */
  #showDialogue() {
    const dataset = this?.dataset?.[0];
    if (isNullOrUndefined(dataset)) {
      return;
    }

    this.activeItem = dataset;
    this.activeData = deepCopy(this?.activeItem?.nodes);

    let renderable;
    let modal = new OntologySelectionModal(this.element, this.activeData, this.options);
    modal.show((dialogue) => {
      const container = dialogue.container;
      renderable = {
        modal: modal,
        dialogue: dialogue,
        reload: () => {
          const targets = container.querySelectorAll('#ontology-source-view > [data-source]');
          const activeId = this.activeItem?.model?.source;
          for (let i = 0; i < targets.length; ++i) {
            let target = targets[i];
            let active = parseInt(target.getAttribute('data-source')) === activeId;
            if (active) {
              target.classList.add('active');
            } else {
              target.classList.remove('active');
            }
          }
          this.renderable?.treeComponent.reload();
        }
      }
      this.renderable = renderable;

      this.#initialiseDialogue();
    })
      .then(state => {

      })
      .catch(e => {
        console.warn(e);
      })
      .finally(() => {
        if (renderable === this.renderable) {
          this.renderable = null;
        }
      });
  }

  /**
   * initialiseDialogue
   * @desc initialises the dialogue renderables, and
   *       any child component(s)
   * 
   */
  #initialiseDialogue() {
    const dialogue = this.renderable.dialogue;
    const container = dialogue.container.querySelector('#ontology-tree-view');
    const ontologyList = dialogue.container.querySelector('#ontology-source-view');
    const activeId = this.activeItem?.model?.source;

    for (let i = 0; i < this.dataset.length; ++i) {
      let dataset = this.dataset[i];
      let html = interpolateString(this.templates.group, {
        source: dataset.model.source,
        label: dataset.model.label,
      });
  
      let component = parseHTMLFromString(html);
      component = ontologyList.appendChild(component.body.children[0]);

      let active = parseInt(component.getAttribute('data-source')) === activeId;
      if (active) {
        component.classList.add('active');
      } else {
        component.classList.remove('active');
      }
      component = component.querySelector('a');

      component.addEventListener('click', this.#handleDatasetChange.bind(this));
    }

    const treeComponent = eleTree({
      el: container,
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

    treeComponent.on('lazyload', this.#handleLoading.bind(this));
    treeComponent.on('checkbox', this.#handleCheckbox.bind(this));
    this.renderable.treeComponent = treeComponent;
  }


  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/

  /**
   * handleAddButton
   * @desc handles the 'Add Ontology' button
   * @param {event} e the assoc. event
   */
  #handleAddButton(e) {
    this.#showDialogue();
  }

  /**
   * handleLoading
   * @desc handles the lazyloading functionality derived from eleTree
   * @param {object} group the assoc. eleTree data
   */
  #handleLoading(group) {
    const data = group.data;
    const load = group.load;

    this.#fetchNodeData(data.id)
      .then(node => load(node.children))
      .catch(console.error);
  }

  /**
   * handleDatasetChange
   * @desc handles dataset source changes via ontology panel
   * @param {event} e the assoc. event data
   */
  #handleDatasetChange(e) {
    e.preventDefault();

    const component = e?.target?.parentNode;
    if (!this.isOpen() || isNullOrUndefined(component)) {
      return;
    }

    const sourceId = parseInt(component.getAttribute('data-source'));
    if (isNaN(sourceId)) {
      return;
    }

    this.#pushDataset(sourceId);
  }

  /**
   * handleCheckbox
   * @desc handles the checkbox change event derived from eleTree
   * @param {object} group the assoc. eleTree data
   */
  #handleCheckbox(group) {
    if (!this.isOpen()) {
      return;
    }

    console.log(this.renderable?.treeComponent.getChecked());
  }
}
