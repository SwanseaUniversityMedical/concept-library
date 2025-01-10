import * as Constants from './constants.js';
import OntologySelectionModal from './modal.js';
import VirtualisedList, { DebouncedTask } from '../../../components/virtualisedList/index.js';

/**
 * @class OntologySelectionService
 * @desc Class that allows the selection of items from arbitrary
 *       directed acyclic graphs that define taggable ontologies
 * 
 */

export default class OntologySelectionService {
  static DataTarget = 'ontology-service';
  #originalValue = null;

  constructor(element, phenotype, componentData, options) {
    this.domain = getBrandedHost();
    this.element = element;
    this.phenotype = phenotype;

    const hasInitData = !isNullOrUndefined(componentData?.dataset);
    this.dataset = hasInitData ? componentData?.dataset : [];
    this.#initialise(componentData, options);

    if (!hasInitData) {
      this.#fetchComponentData()
        .then(dataset => {
          this.dataset.splice(this.dataset.length, 0, ...dataset);
          this.#initialiseTree();
        })
        .catch(console.error);
    }
  }

  /**
   * getLabel
   * @desc derives the label from a given node,
   *       adding any additional properties if available
   * @param {object} node the given node
   * @returns {string} the associated label
   * 
   */
  static getLabel(node) {
    if (typeof(node) !== 'object' || Array.isArray(node)) {
      return '';
    }

    let { label = '', properties = undefined } = node;
    if (!isNullOrUndefined(properties)) {
      let code = properties?.code;
      if (typeof(code) === 'string') {
        label = `${label} (${code})`;
      }
    }

    return label;
  }

  /**
   * applyToTree
   * @desc static method to apply a callback to each node in a tree.
   * 
   *       The recursion can be exited early by returning a truthy value; if a falsy
   *       value is returned from the callback the recursion will continue
   * 
   * @param {array} data the tree structure to recursively iterate
   * @param {function} callback the callback function
   * @returns {boolean|null} a truthy or falsy value derived from the recursion
   * 
   */
  static applyToTree(data, callback) {
    assert(Array.isArray(data), `Expected array as data, got "${typeof(data)}"`)
    assert(typeof(callback) === 'function', `Expected function as callback, got "${typeof(callback)}"`);

    let length = data.length;
    let result = false;
    for (let i = 0; i < length; ++i) {
      let node = data[i];
      result = callback(node);

      if (result) {
        break;
      }

      if (Array.isArray(node?.children) && node.children.length > 0) {
        result = OntologySelectionService.applyToTree(node.children, callback);

        if (result) {
          break;
        }
      }
    }

    return result;
  }

  /**
   * reduceTree
   * @desc reduces a tree such that only nodes which are either:
   *          a) a parent node, assuming all descendants are checked
   *          b) a descendant node, assuming its parents are unselected;
   *             and that its children, if any, are all selected
   * 
   * @param {object} param
   * @param {array}         param.data     the tree structure to recursively iterate
   * @param {function|null} param.callback an optional callback for filtered element(s)
   * @param {array|null}    param.filtered an optional filtered node list 
   * 
   * @returns {array} a filtered node list containing only top-level selected nodes
   * 
   */
  static reduceTree({ data, callback, filtered }) {
    callback = typeof(callback) === 'function' ? callback : null;
    filtered = Array.isArray(filtered) ? filtered : null;

    let length = Array.isArray(data) ? data.length : 0;
    if (!length) {
      return filtered;
    }

    let node, children;
    for (let i = 0; i < length; ++i) {
      node = data[i];
      if (node?.checked === true && (!node?.children || node?.children.length === node?.child_count)) {
        const result = { id: node.id, type_id: node.type_id, label: node?.label };
        if (callback) {
          callback(result);
        }

        if (filtered) {
          filtered.push(result);
        }

        continue;
      }

      children = node?.children;
      if (Array.isArray(children)) {
        this.reduceTree({ data: children, callback, filtered });
      }
    }

    return filtered;
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

  /**
   * isDirty
   * @desc determines whether the value of this component has been modified
   *       from its initial value
   * 
   * @returns {bool} returns the dirty state of this component
   */
  isDirty() {
    return hasDeltaDiff(
      this.#originalValue.map(x => x.id),
      this.value.map(x => x.id)
    );
  }

  /**
   * getValue
   * @desc gets the current value of the component
   * @param {boolean} flat whether to return the value as a flat list of ids
   * @returns {object[]} returns an array of objects containing the current value
   *  
   */
  getValue(flat = false) {
    if (flat) {
      return this.value.map(x => x.id);
    }

    return deepCopy(this.value);
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
   * @param {object} componentData component data, e.g. the dataset and associated value(s)
   * @param {object|null} options optional parameters
   */
  #initialise(componentData, options) {
    this.options = mergeObjects(options || { }, Constants.OPTIONS);

    this.#initialiseTree();
    this.#computeComponentValue(componentData?.value);

    // Initialise element & child template(s)
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
    this.#renderCreateComponent();
  }

  /**
   * initialiseTree
   * @desc initialises the tree view
   * 
   */
  #initialiseTree() {
    const dataset = this.dataset
    if (isNullOrUndefined(dataset)) {
      return;
    }

    for (let i = 0; i < dataset.length; ++i) {
      OntologySelectionService.applyToTree(dataset[i].nodes, elem => {
        if ((isNullOrUndefined(elem.label) || typeof elem.label === 'string') && !elem.processed) {
          elem.label = OntologySelectionService.getLabel(elem);
          elem.processed = true;
        }
      });
    }
  }

  /**
   * fetchComponentData
   * @desc fetches initialisation data
   * @returns Promise<Array> the component's initialisation data
   */
  async #fetchComponentData() {
    return fetch(
      `${getBrandedHost()}/api/v1/ontology/`,
      {
        method: 'GET',
        headers: {
          'X-Target': 'get_options',
          'X-Requested-With': 'XMLHttpRequest',
        }
      }
    )
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to GET ontology options with Err<code: ${response.status}> and response:\n${response}`);
        }

        return response.json();
      })
      .then(dataset => {
        if (!(dataset instanceof Object) || !Array.isArray(dataset)) {
          throw new Error(`Expected ontology init data to be an object with a result array, got ${dataset}`);
        }

        return dataset;
      });
  }

  /**
   * computeComponentValue
   * @desc computes the component data, given a dict containing the ancestry & value
   * @param {object} param
   * @param {object|null} param.ancestors   optional ancestor-related data to be spliced into the tree
   * @param {array|null}  param.value       optional value for this field, e.g. when editing
   * @returns {object} this class for chaining
   * 
   */
  #computeComponentValue({ ancestors = undefined, value = [] } = { }) {
    this.value = Array.isArray(value) ? value : [];

    if (Array.isArray(ancestors)) {
      OntologySelectionService.applyToTree(ancestors, elem => {
        if (typeof(elem?.label) === 'string' && !elem?.processed) {
          elem.label = OntologySelectionService.getLabel(elem);
          elem.processed = true;
        }
      });

      for (let i = 0; i < ancestors.length; ++i) {
        let nodeList = ancestors[i];
        if (!Array.isArray(nodeList)) {
          continue;
        }

        for (let j = 0; j < nodeList.length; ++j) {
          let node = nodeList[j];
          let dataset = this.dataset.findIndex(x => x.model.source == node.type_id);
          dataset = dataset >= 0 ? this.dataset[dataset] : null;
          if (isNullOrUndefined(dataset)) {
            continue;
          }

          OntologySelectionService.applyToTree(dataset.nodes, elem => {
            if (elem.id !== node.id) {
              return false;
            }

            if (node?.children && elem?.children) {
              for (let k = 0; k < node.children; ++k) {
                let child = node.children[k];
                if (!isNullOrUndefined(elem.children.find(x => x.id === child.id))) {
                  continue;
                }

                elem.children.push(child);
              }
            } else {
              elem.children = node.children;
            }
            elem.parents = node.parents;

            return true;
          });
        }
      }
    }

    for (let j = 0; j < this.value.length; ++j) {
      let selected = this.value[j];
      if (selected?.processed) {
        continue;
      }

      selected.label = OntologySelectionService.getLabel(selected);
      selected.processed = true;
    }

    this.#originalValue = deepCopy(this.value);
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
      { host: this.domain, id: id.toString() }
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
    data.push(...deepCopy(dataset.nodes));
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

    const selectedItems = this.selectedItems;
    const activeSourceId = this.activeItem?.model?.source;

    const treeComponent = this.renderable.treeComponent;
    const selectionComponent = this.renderable.selectionComponent;

    const hashmap = { };
    const hasSeen = { };
    OntologySelectionService.reduceTree({
      data: treeComponent.getAllNodeData(),
      callback: (node) => {
        const { id, type_id, label } = node;
        const index = selectedItems.findIndex(x => x?.id === id && x?.type_id === activeSourceId);
        if (index < 0) {
          selectedItems.push({ id, type_id, label });
        }

        hashmap[id] = true;
      }
    });

    let i = 0;
    while (i < selectedItems.length) {
      let elem = selectedItems[i];
      const id = elem?.id;
      const sourceId = elem?.type_id;
      if (sourceId === activeSourceId) {
        if (!isNullOrUndefined(hasSeen?.[id]) || isNullOrUndefined(hashmap?.[id])) {
          selectedItems.splice(i, 1)
          continue;
        }

        hasSeen[id] = true;
      }

      i++;
    }

    const length = selectedItems.length;
    selectionComponent.setCount(length);
    selectionComponent.refresh();
    return this.#toggleSelectionView(length);
  }

  /**
   * instantiateObserverGroup
   * @desc instantiates a task group and a resize observer to observe
   *       the size of components across their lifetime and to defer
   *       the virtual list update(s) required
   * 
   *       Ref @ https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver
   * 
   * @returns {object{observer: ResizeObserver, group: DebouncedTask}} the resulting instances
   * 
   */
  #instantiateObserverGroup() {
    let debouncedTask = new DebouncedTask(this.#computeBlockSizes.bind(this), 200);
    return {
      group: debouncedTask,
      observer: new ResizeObserver(() => {
        debouncedTask();
      }),
    }
  }

  /**
   * computeBlockSize
   * @desc computes the block height of the rendered virtualised components
   * 
   */
  #computeBlockSizes() {
    if (!this.isOpen()) {
      return;
    }

    const component = this.renderable?.selectionComponent;
    const renderables = !isNullOrUndefined(component) ? component.getRenderables() : [];

    const sizes = [];
    for (let i = 0; i < renderables.length; ++i) {
      let elem = renderables[i];
      let index = parseInt(elem?.getAttribute('data-key'));
      if (typeof(index) !== 'number' || isNaN(index)) {
        continue;
      }

      let height = Math.max(elem?.clientHeight || 0, component.getHeight(i) || 0);
      sizes.push([ index, height ]);
    }

    if (!!sizes.length) {
      component.resizeItems(sizes);
    }
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

    this.activeItem = [];
    this.activeData = [];
    this.selectedItems = deepCopy(this.value);

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

          const checked = this.selectedItems.reduce((filtered, e) => {
            const id = e?.id;
            const sourceId = e?.type_id;
            if (!isNullOrUndefined(id) && sourceId === activeId) {
              filtered.push(id);
            }

            return filtered;
          }, []);
          this.renderable?.treeComponent.reload();

          if (checked.length > 0) {
            this.renderable?.treeComponent.setChecked(checked, true);
          }
        }
      }
      this.renderable = renderable;

      this.#initialiseDialogue();
      this.#pushDataset(0);
      this.#resolveSelectedItems();
    })
      .then(state => {
        if (renderable !== this.renderable) {
          return;
        }

        switch (state) {
          case Constants.EVENT_STATES.CONFIRMED: {
            this.value = deepCopy(this.selectedItems);
            this.#renderCreateComponent();
          } break;

          default: {
            /* Rejection handler? */

          } break;
        }
      })
      .catch(e => {
        console.warn(`OntologySelectionService encountered an error:\n\n${String(e)}`);
      })
      .finally(() => {
        if (renderable === this.renderable) {
          this.renderable = null;
          this.activeData = null;
          this.activeItem = null;
          this.selectedItems = null;
        }

        let resizeObserverGroup = renderable.resizeObserverGroup;
        if (!isNullOrUndefined(resizeObserverGroup)) {
          if (resizeObserverGroup?.observer) {
            resizeObserverGroup.observer.disconnect();
            delete resizeObserverGroup.observer;
          }

          if (resizeObserverGroup?.group) {
            resizeObserverGroup.group.clear();
            delete resizeObserverGroup.group;
          }
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
        source: dataset.model.source.toFixed(0),
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
    const resizeObserverGroup = this.#instantiateObserverGroup();

    const selectionComponent = new VirtualisedList(
      selectionContainer,
      {
        count: selectedLength,
        height: 0,
        onPaint: (elem, index, height) => {
          if (!elem.parentElement) {
            return;
          }

          onElementRemoved(elem)
            .then(() => resizeObserverGroup?.observer?.unobserve(elem))
            .catch(console.error);

          resizeObserverGroup?.observer?.observe(elem);
        },
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

          return component;
        }
      }
    );

    const { scrollingFrame } = selectionComponent.getComponents();
    scrollingFrame.classList.add('slim-scrollbar');
    this.renderable.selectionComponent = selectionComponent;
    this.renderable.resizeObserverGroup = resizeObserverGroup
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

  /**
   * renderCreateComponent
   * @desc handles the rendering of items on the main `./create`
   *       and `./update` pages
   * 
   * @returns {object} this object, an instance of this class
   * 
   */
  #renderCreateComponent() {
    const noneAvailable = this.element.querySelector('#no-available-ontology');
    const ontologyView = this.element.querySelector('#ontology-creator');

    const value = this.value;
    const length = value.length;
    if (length < 1) {
      noneAvailable.classList.add('show');
      ontologyView.classList.remove('show');
    } else {
      noneAvailable.classList.remove('show');
      ontologyView.classList.add('show');

      const ontologyList = ontologyView.querySelector('#ontology-list');
      clearAllChildren(ontologyList);

      const sources = { };
      this.dataset.forEach(x => {
        sources[x.model.source] = x.model.label;
      });

      const sorted = deepCopy(this.value);
      sorted.sort((a, b) => a.type_id < b.type_id ? -1 : (a.type_id > b.type_id ? 1 : 0));

      let currentGroup;
      for (let i = 0; i < length; ++i) {
        let { type_id, label } = sorted[i];
        if (currentGroup !== type_id) {
          currentGroup = type_id;

          let html = interpolateString(this.templates.group, {
            source: type_id,
            label: sources[type_id],
          });

          let component = parseHTMLFromString(html);
          component = ontologyList.appendChild(component.body.children[0]);
        }

        let html = interpolateString(this.templates.value, { label: label });

        let component = parseHTMLFromString(html);
        component = ontologyList.appendChild(component.body.children[0]);
      }
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

    const targetId = parseInt(target.getAttribute('data-id'));
    const targetSourceId = parseInt(target.getAttribute('data-group'));
    const activeSourceId = this.activeItem?.model?.source;

    if (targetSourceId === activeSourceId) {
      this.renderable.treeComponent.unChecked([parseInt(targetId)]);
    } else {
      const index = this.selectedItems.findIndex(x => x?.id === targetId && x?.type_id === targetSourceId);
      if (index >= 0) {
        this.selectedItems.splice(index, 1);
      }
    }
    this.#resolveSelectedItems();
  }

  /**
   * handleLoading
   * @desc handles the lazyloading functionality derived from eleTree
   * @param {object} group the assoc. eleTree data
   */
  #handleLoading(group) {
    const { data, load } = group;
    const sourceId = data?.type_id;
    const dataIndex = this.dataset.findIndex(e => e?.model?.source == sourceId);
    const dataset = dataIndex >= 0 ? this.dataset[dataIndex] : null;
    if (isNullOrUndefined(dataset)) {
      return;
    }

    let children;
    OntologySelectionService.applyToTree(dataset.nodes, elem => {
      if (elem?.id === data.id) {
        if (Array.isArray(elem?.children) && elem.children.length === elem.child_count) {
          children = deepCopy(elem.children);
        }

        return true;
      }

      return false;
    });

    if (!isNullOrUndefined(children)) {
      load([]);
      this.#resolveSelectedItems()
      return;
    }

    const treeComponent = this.renderable.treeComponent;
    this.#fetchNodeData(data.id)
      .then(async node => {
        const isRoot = node.isRoot;
        const isLeaf = node.isLeaf;

        OntologySelectionService.applyToTree(node.children, elem => {
          if (typeof(elem?.label) === 'string' && !elem?.processed) {
            elem.label = OntologySelectionService.getLabel(elem);
            elem.processed = true;
          }
        });

        if (isRoot) {
          for (let i = 0; i < dataset.nodes.length; ++i) {
            const elem = dataset.nodes[i];
            const { id } = elem;
            if (id === node.id) {
              const newChildren = node.children.filter(x => !elem?.children || elem.children.findIndex(e => e.id === x.id) < 0);
              const newAncestors = node.parents.filter(x => !elem?.parents || !elem.parents.includes(x.id));
              elem.children = [...deepCopy(newChildren), ...(elem?.children || [])];
              elem.parents = [...deepCopy(newAncestors), ...(elem?.parents || [])];
            }
          }
        } else if (!isLeaf) {
          OntologySelectionService.applyToTree(dataset.nodes, elem => {
            const { id } = elem;
            if (id === node.id) {
              const newChildren = node.children.filter(x => !elem?.children || elem.children.findIndex(e => e.id === x.id) < 0);
              const newAncestors = node.parents.filter(x => !elem?.parents || !elem.parents.includes(x.id));
              elem.children = [...deepCopy(newChildren), ...(elem?.children || [])];
              elem.parents = [...deepCopy(newAncestors), ...(elem?.parents || [])];
            }
          });
        }

        const mapped = { };
        children = deepCopy(node.children);
        for (let i = 0; i < children.length; ++i) {
          let child = children[i];
          let parents = child?.parents;
          if (!Array.isArray(parents)) {
            continue;
          }

          for (let j = 0; j < parents.length; ++j) {
            let parentId = parents[j];
            if (isNullOrUndefined(parentId) || parentId === node.id) {
              continue;
            }

            if (!mapped.hasOwnProperty(parentId)) {
              mapped[parentId] = [];
            }

            if (!mapped[parentId].includes(child.id)) {
              mapped[parentId].push(child);
            }
          }
        }

        OntologySelectionService.applyToTree(treeComponent.getAllNodeData(), elem => {
          const { id } = elem;
          if (mapped[id]) {
            if (!Array.isArray(elem.children)) {
              elem.children = [...deepCopy(mapped[id])];
            } else {
              const related = mapped[id].filter(e => elem.children.findIndex(x => x.id === e.id) < 0);
              for (let i = 0; i < related; ++i) {
                elem.children.push(deepCopy(related[i]));
              }
            }
          }
        });

        load(children);
      })
      .then(() => this.#resolveSelectedItems())
      .then(() => treeComponent.setChecked(
        this.selectedItems.map(x => x.id)
      ))
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
    this.#resolveSelectedItems();
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

    const { id, checked } = group.data;
    if (!checked) {
      this.renderable.treeComponent.unChecked([id]);
    }

    this.#resolveSelectedItems();
    this.renderable.treeComponent.setChecked(this.selectedItems.map(x => x.id));
  }
}
