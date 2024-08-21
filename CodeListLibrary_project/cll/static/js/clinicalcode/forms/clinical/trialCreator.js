/**
 * PUBLICATION_OPTIONS
 * @desc describes the optional parameters for this class
 * 
 */
const TRIAL_OPTIONS = {
  // The minimum message duration for toast notif popups
  notificationDuration: 5000,

  /* Attribute name(s) */
  //  - dataAttribute: defines the attribute that's used to retrieve contextual data
  dataAttribute: 'data-field',
  //  - targetAttribute: defines the data target for individual elements which defines their index
  targetAttribute: 'data-target',

  /* Related element IDs */
  //  - textInputId: describes the text input box for publication details
  idInputId: '#id-input-box',
  //  - doiInputId: describes the DOI text input box
  linkInputId: '#link-input-box',
  //  - primaryTrialCheckboxId: describes the primary publication checkbox
  primaryTrialCheckboxId: '#primary-trial-checkbox',
  nameInputId: '#name-input-box',
  //  - addButtonId: describes the 'Add' button used to add publications
  addButtonId: '#add-input-btn',
  //  - availabilityId: describes the 'No available publications' element
  availabilityId: '#no-available-trials',
  //  - publicationGroupId: describes the parent element of the publication list
  trialGroupId: '#trial-group',
  //  - publicationListId: describes the publication list in which elements are held
  trialListId: '#trial-list',
};


/**
 * PUBLICATION_ITEM_ELEMENT
 * @desc describes the publication item element and its interpolable targets
 * 
 */
const TRIAL_ITEM_ELEMENT = '<div class="publication-list-group__list-item" data-target="${index}"> \
  <div class="publication-list-group__list-item-url"> \
    <p>${id}${link}${name}</p> \
    ${primary === 1 ? \'<p>Primary</p>\' : \'\'}\
  </div> \
  <button class="publication-list-group__list-item-btn" data-target="${index}"> \
    <span class="delete-icon"></span> \
    <span>Remove</span> \
  </button> \
</div>';

/**
 * PUBLICATION_DOI_ELEMENT
 * @desc describes the optional publication DOI element
 *       and its interpolable targets
 *
 */
const TRIAL_LINK_ELEMENT = '<br/><br/><a href="${link}">${link}</a>';


export default class TrialCreator {
  constructor(element, data, options) {
    this.data = Array.isArray(data) ? data : [ ];
    this.dirty = false;
    this.element = element;

    // parse opts
    if (!isObjectType(options)) {
      options = { };
    }
    this.options = mergeObjects(options, TRIAL_OPTIONS);
 
    // init
    this.#setUp();
    this.#redrawTrials();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getData
   * @returns {object} the publication data
   */
  getData() {
    return this.data;
  }

  /**
   * getElement
   * @returns {node} the assoc. element
   */
  getElement() {
    return this.element;
  }

  /**
   * isDirty
   * @returns {bool} returns the dirty state of this component
   */
  isDirty() {
    return this.dirty;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/
  /**
   * makeDirty
   * @desc informs the top-level parent that we're dirty
   *       and updates our internal dirty state
   * @return {object} return this for chaining
   */
  makeDirty() {
    window.entityForm.makeDirty();
    this.dirty = true;
    return this;
  }

  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * drawItem
   * @param {int} index the index of the publication in our data
   * @param id
   * @param {string} link the publication name
   * @param {string} name Primary Publication Flag
   * @param {int} primary Primary Publication Flag
   * @returns {string} html string representing the element
   */
  #drawItem(index, id, link, name, primary) {

    let linkElement;
    if (!isNullOrUndefined(link) && !isStringEmpty(link)) {
      linkElement = interpolateString(TRIAL_LINK_ELEMENT, { link: link });
    } else {
      linkElement = '';
    }

    return interpolateString(TRIAL_ITEM_ELEMENT, {
      index: index,
      id: id,
      link: linkElement,
      name: name,
      primary: primary

    });
  }

  /**
   * redrawPublications
   * @desc redraws the entire publication list
   */
  #redrawTrials() {
    this.dataResult.innerText = JSON.stringify(this.data);
    this.renderables.list.innerHTML = '';
    
    if (this.data.length > 0) {
      this.renderables.group.classList.add('show');
      this.renderables.none.classList.remove('show');

      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(i, this.data[i]?.id, this.data[i]?.link,  this.data[i].name,  this.data[i]?.primary);
        this.renderables.list.insertAdjacentHTML('beforeend', node);
      }

      return;
    }

    this.renderables.none.classList.add('show');
    this.renderables.group.classList.remove('show');
  }

  /**
   * setUp
   * @desc initialises the publication component
   */
  #setUp() {
    this.regId = this.element.querySelector(this.options.idInputId);
    this.regLink = this.element.querySelector(this.options.linkInputId);
    this.trialName = this.element.querySelector(this.options.nameInputId);
    this.primaryTrialCheckbox = this.element.querySelector(this.options.primaryTrialCheckboxId);

    this.addButton = this.element.querySelector(this.options.addButtonId);
    this.addButton.addEventListener('click', this.#handleInput.bind(this));
    window.addEventListener('click', this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector(this.options.availabilityId);
    const trialGroup = this.element.parentNode.querySelector(this.options.trialGroupId);
    const trialList = this.element.parentNode.querySelector(this.options.trialListId);
    console.log(trialList)
    this.renderables = {
      none: noneAvailable,
      group: trialGroup,
      list: trialList,
    }

    const attr = this.element.getAttribute(this.options.dataAttribute);
    this.dataResult = this.element.parentNode.querySelector(`[for="${attr}"]`);
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleInput
   * @desc bindable event handler for key up events of the publication input box
   * @param {event} e the event of the input 
   */
  #handleInput(e) {
    e.preventDefault();
    e.stopPropagation();

    const id = this.regId.value;
    const link = this.regLink.value;
    const name = this.trialName.value;
    const primary= Number(this.primaryTrialCheckbox.checked ? this.primaryTrialCheckbox.dataset.value: '0');


    this.regId.value = '';
    this.regLink.value = '';
    this.trialName.value = '';
    this.primaryTrialCheckbox.checked = false;
    this.data.push(
        {
          id: id,
          link: link,
          name: name,
          primary: primary
        }
        );
    this.makeDirty();
    
    this.#redrawTrials();
  }

  /**
   * handleClick
   * @desc bindable event handler for click events of the publication item's delete button
   * @param {event} e the event of the input 
   */
  #handleClick(e) {
    const target = e.target;
    if (!target || !this.renderables.list.contains(target)) {
      return;
    }

    if (target.nodeName !== 'BUTTON') {
      return;
    }

    const index = target.getAttribute(this.options.targetAttribute);
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawTrials();
    this.makeDirty();
  }
}
