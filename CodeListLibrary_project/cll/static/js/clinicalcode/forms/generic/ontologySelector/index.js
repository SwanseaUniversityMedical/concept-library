import * as Constants from './constants.js';
import OntologySelectionModal from './modal.js';
import VirtualisedList from '../../../components/virtualisedList/index.js';

/**
 * @class OntologySelectionService
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

  /**
   * resolveSelected
   * @desc resolves the selected item list based on currently checked item(s)
   * @returns {object} this class for chaining
   * 
   */
  #resolveSelectedItems() {
    if (!this.isOpen()) {
      return this;
    }

    const hashmap = { };
    const sourceId = this.activeItem?.model?.source;
    const selectedItems = this.selectedItems;
    const treeComponent = this.renderable.treeComponent;
    const selectionComponent = this.renderable.selectionComponent;

    /* TODO: Sieve leaf nodes if their parents are completely selected */

    treeComponent.getChecked().forEach(e => {
      if (e?.type_id !== sourceId) {
        return;
      }

      const id = e?.id;
      const index = selectedItems.findIndex(x => x?.id === id && x?.type_id === sourceId);
      if (index < 0) {
        selectedItems.push({ id: id, type_id: sourceId, label: e?.label });
      }

      hashmap[id] = true;
    });

    let i = 0;
    while (i < selectedItems.length) {
      let elem = selectedItems[i];
      if (elem?.type_id !== sourceId) {
        i++;
        continue;
      }

      const id = elem?.id;
      if (isNullOrUndefined(hashmap?.[id])) {
        selectedItems.splice(i, 1)
        continue;
      }

      i++;
    }

    const length = selectedItems.length;
    selectionComponent.setCount(length);
    selectionComponent.refresh();
    return this.#toggleSelectionView(length);
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
    this.activeData = [...dataset.nodes];

    /* TODO: Parse selected items from value list */
    this.selectedItems = [];

    let renderable;
    let modal = new OntologySelectionModal(this.element, this.options);
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
    const activeId = this.activeItem?.model?.source;
    const dialogue = this.renderable.dialogue;

    const treeContainer = dialogue.container.querySelector('#ontology-tree-view');
    const ontologyContainer = dialogue.container.querySelector('#ontology-source-view');
    const selectionContainer = dialogue.container.querySelector('#ontology-selected-view');

    // Initialise ontology sources
    for (let i = 0; i < this.dataset.length; ++i) {
      let dataset = this.dataset[i];
      let html = interpolateString(this.templates.source, {
        source: dataset.model.source,
        label: dataset.model.label,
      });

      let component = parseHTMLFromString(html);
      component = ontologyContainer.appendChild(component.body.children[0]);

      let active = parseInt(component.getAttribute('data-source')) === activeId;
      if (active) {
        component.classList.add('active');
      } else {
        component.classList.remove('active');
      }

      component = component.querySelector('a');
      component.addEventListener('click', this.#handleDatasetChange.bind(this));
    }

    // Initialise tree view
    const treeComponent = eleTree({
      el: treeContainer,
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

    // Initialise selection view
    const selectedItems = this.selectedItems;
    const selectedLength = selectedItems.length;
    const selectionComponent = new VirtualisedList(
      selectionContainer,
      {
        count: selectedLength,
        height: 0,
        onRender: (index, height) => {
          let selectedItem = selectedItems[index];
          if (!selectedItem) {
            return document.createElement('div');
          }

          const html = interpolateString(this.templates.item, {
            id: selectedItem?.id,
            source: selectedItem?.type_id,
            label: selectedItem?.label,
          });

          let component = parseHTMLFromString(html);
          component = component.body.children[0];
          
          const btn = component.querySelector('[data-target="delete"]');
          btn.addEventListener('click', this.#handleDeleteButton.bind(this));

          if (height == 0) {
            setTimeout(() => {
              selectionComponent.setItemHeight(index, component.clientHeight);
            }, 100);
          }

          return component;
        }
      }
    );

    const { scrollingFrame } = selectionComponent.getComponents();
    scrollingFrame.classList.add('slim-scrollbar');

    this.renderable.selectionComponent = selectionComponent;
    this.#toggleSelectionView(selectedLength);
  }

  /**
   * toggleSelectionView
   * @desc responsible for toggling the 'no-items-selected' renderable section
   *       for the selected view
   * @param {number} size expects the size of the selection list to derive visibility
   * @returns {object} returns this for chaining
   * 
   */
  #toggleSelectionView(size) {
    if (!this.isOpen()) {
      return this;
    }

    const dialogue = this.renderable.dialogue;
    const noneSelected = dialogue.container.querySelector('#no-items-selected');
    const listSelection = dialogue.container.querySelector('#ontology-selected-view');

    if (size > 0) {
      noneSelected.classList.remove('show');
      listSelection.classList.add('show');
    } else {
      noneSelected.classList.add('show');
      listSelection.classList.remove('show');
    }

    return this;
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
   * handleDeleteButton
   * @desc handles the trash icon button for selected item(s)
   * @param {event} e the assoc. event
   */
  #handleDeleteButton(e) {
    if (!this.isOpen()) {
      return;
    }

    const target = e.target;
    if (isNullOrUndefined(target)) {
      return;
    }

    const targetId = target.getAttribute('data-id');
    this.renderable.treeComponent.unChecked([parseInt(targetId)]);
    this.#resolveSelectedItems();
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
      .then(() => this.#resolveSelectedItems())
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

    this.#resolveSelectedItems();
  }
}
