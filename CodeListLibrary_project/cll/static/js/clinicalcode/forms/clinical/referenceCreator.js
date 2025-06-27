import { TOAST_MSG_DURATION } from '../entityFormConstants.js';

/**
 * REFERENCE_OPTIONS
 * @desc describes the optional parameters for this class
 * 
 */
const REFERENCE_OPTIONS = {
  // The minimum message duration for toast notif popups
  notificationDuration: TOAST_MSG_DURATION,

  /* Attribute name(s) */
  //  - dataAttribute: defines the attribute that's used to retrieve contextual data
  dataAttribute: 'data-field',
  //  - targetAttribute: defines the data target for individual elements which defines their index
  targetAttribute: 'data-target',

  /* Related element IDs */
  //  - textInputId: describes the text input box for reference title
  titleInputId: '#reference-title-input-box',
  //  - urlInputId: describes the url text input box
  urlInputId: '#url-input-box',
  //  - primaryPubCheckboxId: describes the primary reference checkbox
  addButtonId: '#add-input-btn',
  //  - availabilityId: describes the 'No available reference's element
  availabilityId: '#no-available-references',
  //  - referenceGroupId: describes the parent element of the reference list
  referenceGroupId: '#reference-group',
  //  - referenceListId: describes the reference list in which elements are held
  referenceListId: '#reference-list',
};


/**
 * REFERENCE_ITEM_ELEMENT
 * @desc describes the reference item element and its interpolable targets
 * 
 */
const REFERENCE_ITEM_ELEMENT = '<div class="publication-list-group__list-item" data-target="${index}"> \
  <div class="publication-list-group__list-item-url"> \
    <p>title: ${title} &nbsp; url: <a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a></p> \
  </div> \
  <button class="publication-list-group__list-item-btn" data-target="${index}"> \
    <span class="delete-icon"></span> \
    <span>Remove</span> \
  </button> \
</div>';


/**
 * REFERENCE_NOTIFICATIONS
 * @desc notification text that is used to present information
 *       to the client, _e.g._ to inform them of a validation
 *       error, or to confirm them of a forced change _etc_
 * 
 */
const REFERENCE_NOTIFICATIONS = {
  // e.g. in the case of a user providing a DOI
  //      that isn't matched by utils.js' `CLU_DOI_PATTERN` regex
  InvalidURLProvided: 'We couldn\'t validate the url you provided. Are you sure it\'s correct?',
}


/**
 * @class ReferenceCreator
 * @desc A class that can be used to control reference lists
 * 
 * e.g.
 * 
  ```js
    // initialise
    const startValue = [
      { details: 'some reference title', doi?: 'some optional DOI' },
      { details: 'some other title', doi?: 'some other optional DOI' }
    ];

    const element = document.querySelector('#reference-component');
    const creator = new referenceCreator(element, startValue);

    // ...when retrieving data
    if (creator.isDirty()) {
      const data = creator.getData();
      
      // TODO: some save method


    }
  ```
 * 
 */
export default class ReferenceCreator {
  constructor(element, data, options) {
    this.data = Array.isArray(data) ? data : [ ];
    this.dirty = false;
    this.element = element;

    // parse opts
    if (!isObjectType(options)) {
      options = { };
    }
    this.options = mergeObjects(options, REFERENCE_OPTIONS);
 
    // init
    this.#setUp();
    this.#redrawReferences();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getData
   * @returns {object} the reference data
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
   * @param {int} index the index of the reference in our data
   * @param {url} url the reference url
   * @param {string} title the reference name
   * @returns {string} html string representing the element
   */
  #drawItem(index, url, title) {
    let urlElement;
    if (isNullOrUndefined(url) && isStringEmpty(url)) {
      urlElement = '';
    } else {
      urlElement = url
    }

    return interpolateString(REFERENCE_ITEM_ELEMENT, {
      index: index,
      title: title,
      url: urlElement,
    });
  }

  /**
   * redrawReferences
   * @desc redraws the entire reference list
   */
  #redrawReferences() {
    this.dataResult.innerText = JSON.stringify(this.data);
    this.renderables.list.innerHTML = '';
    
    if (this.data.length > 0) {
      this.renderables.group.classList.add('show');
      this.renderables.none.classList.remove('show');

      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(i, this.data[i]?.url, this.data[i]?.title);
        this.renderables.list.insertAdjacentHTML('beforeend', node);
      }

      return;
    }

    this.renderables.none.classList.add('show');
    this.renderables.group.classList.remove('show');
  }

  /**
   * setUp
   * @desc initialises the reference component
   */
  #setUp() {
    this.tileInput = this.element.querySelector(this.options.titleInputId);
    this.urlInput = this.element.querySelector(this.options.urlInputId);

    this.addButton = this.element.querySelector(this.options.addButtonId);
    this.addButton.addEventListener('click', this.#handleInput.bind(this));
    window.addEventListener('click', this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector(this.options.availabilityId);
    const referenceGroup = this.element.parentNode.querySelector(this.options.referenceGroupId);
    const referenceList = this.element.parentNode.querySelector(this.options.referenceListId);
    this.renderables = {
      none: noneAvailable,
      group: referenceGroup,
      list: referenceList,
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
   * @desc bindable event handler for key up events of the reference input box
   * @param {event} e the event of the input 
   */
  #handleInput(e) {
    e.preventDefault();
    e.stopPropagation();

    const url = strictSanitiseString(this.urlInput.value);
    const title = strictSanitiseString(this.tileInput.value);

    if (!this.tileInput.checkValidity() || isNullOrUndefined(title) || isStringEmpty(title)) {
      window.ToastFactory.push({
        type: 'danger',
        message: 'Incorrect reference details provided',
        duration: this.options.notificationDuration,
      });

      this.urlInput.value = url;
      this.tileInput.value = title;

      return;
    }

    const matches = parseString(url, CLU_URL_PATTERN);
    if (!matches?.[0]) {
      window.ToastFactory.push({
        type: 'danger',
        message: REFERENCE_NOTIFICATIONS.InvalidURLProvided,
        duration: this.options.notificationDuration,
      });
    }

    this.urlInput.value = '';
    this.tileInput.value = '';
    this.data.push({
      title: title,
      url: matches?.[0]
    });

    this.makeDirty();
    this.#redrawReferences();
  }

  /**
   * handleClick
   * @desc bindable event handler for click events of the reference item's delete button
   * @param {event} e the event of the input 
   */
  #handleClick(e) {
    const target = e.target;
    if (!target || !this.renderables.list.contains(target)) {
      return;
    }

    if (target.nodeName != 'BUTTON') {
      return;
    }

    const index = target.getAttribute(this.options.targetAttribute);
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawReferences();
    this.makeDirty();
  }
}
