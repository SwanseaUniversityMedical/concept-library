import { PUBLICATION_MIN_MSG_DURATION } from '../entityFormConstants.js';

/**
 * PUBLICATION_OPTIONS
 * @desc describes the optional parameters for this class
 * 
 */
const PUBLICATION_OPTIONS = {
  // The minimum message duration for toast notif popups
  notificationDuration: PUBLICATION_MIN_MSG_DURATION,

  /* Attribute name(s) */
  //  - dataAttribute: defines the attribute that's used to retrieve contextual data
  dataAttribute: 'data-field',
  //  - targetAttribute: defines the data target for individual elements which defines their index
  targetAttribute: 'data-target',

  /* Related element IDs */
  //  - textInputId: describes the text input box for publication details
  textInputId: '#publication-input-box',
  //  - doiInputId: describes the DOI text input box
  doiInputId: '#doi-input-box',
  //  - primaryPubCheckboxId: describes the primary publication checkbox
  primaryPubCheckboxId: '#primary-publication-checkbox',
  //  - addButtonId: describes the 'Add' button used to add publications
  addButtonId: '#add-input-btn',
  //  - availabilityId: describes the 'No available publications' element
  availabilityId: '#no-available-publications',
  //  - publicationGroupId: describes the parent element of the publication list
  publicationGroupId: '#publication-group',
  //  - publicationListId: describes the publication list in which elements are held
  publicationListId: '#publication-list',
};


/**
 * PUBLICATION_ITEM_ELEMENT
 * @desc describes the publication item element and its interpolable targets
 * 
 */
const PUBLICATION_ITEM_ELEMENT = '<div class="publication-list-group__list-item" data-target="${index}"> \
  <div class="publication-list-group__list-item-names"> \
    <p> \
      ${primary === 1 ? \'<span class="publication-list-group__list-item--is-primary"></span>\' : \'\'} \
      ${publication}${doiElement} \
    </p> \
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
const PUBLICATION_DOI_ELEMENT = '<br/><br/><a href="https://doi.org/${doi}" target=_blank rel="noopener">${doi}</a>';


/**
 * PUBLICATION_NOTIFICATIONS
 * @desc notification text that is used to present information
 *       to the client, _e.g._ to inform them of a validation
 *       error, or to confirm them of a forced change _etc_
 * 
 */
const PUBLICATION_NOTIFICATIONS = {
  // e.g. in the case of a user providing a DOI
  //      that isn't matched by utils.js' `CLU_DOI_PATTERN` regex
  InvalidDOIProvided: 'We couldn\'t validate the DOI you provided. Are you sure it\'s correct?',
}


/**
 * @class PublicationCreator
 * @desc A class that can be used to control publication lists
 * 
 * e.g.
 * 
  ```js
    // initialise
    const startValue = [
      { details: 'some publication title', doi?: 'some optional DOI' },
      { details: 'some other title', doi?: 'some other optional DOI' }
    ];

    const element = document.querySelector('#publication-component');
    const creator = new PublicationCreator(element, startValue);

    // ...when retrieving data
    if (creator.isDirty()) {
      const data = creator.getData();
      
      // TODO: some save method


    }
  ```
 * 
 */
export default class PublicationCreator {
  constructor(element, data, options) {
    this.data = Array.isArray(data) ? data : [ ];
    this.dirty = false;
    this.element = element;

    // parse opts
    if (!isObjectType(options)) {
      options = { };
    }
    this.options = mergeObjects(options, PUBLICATION_OPTIONS);
 
    // init
    this.#setUp();
    this.#redrawPublications();
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
   * @param doi
   * @param {string} publication the publication name
   * @param {int} primary Primary Publication Flag
   * @returns {string} html string representing the element
   */
  #drawItem(index, doi, publication, primary) {
    let doiElement;
    if (!isNullOrUndefined(doi) && !isStringEmpty(doi)) {
      doiElement = interpolateString(PUBLICATION_DOI_ELEMENT, { doi: doi });
    } else {
      doiElement = '';
    }

    return interpolateString(PUBLICATION_ITEM_ELEMENT, {
      index: index,
      doiElement: doiElement,
      publication: publication,
      primary: primary
    });
  }

  /**
   * redrawPublications
   * @desc redraws the entire publication list
   */
  #redrawPublications() {
    this.dataResult.innerText = JSON.stringify(this.data);
    this.renderables.list.innerHTML = '';

    if (this.data.length > 0) {
      this.renderables.group.classList.add('show');
      this.renderables.none.classList.remove('show');

      this.data.sort((a, b) => {
        let { details: t0, primary: p0 } = a;
        p0 = typeof p0 === 'boolean' ? Number(p0) : p0;

        let { details: t1, primary: p1 } = b;
        p1 = typeof p1 === 'boolean' ? Number(p1) : p1;

        const twoPrimary = typeof p0 === 'number' && typeof p1 === 'number';
        const equalPrimary = p0 === p1;
        if (twoPrimary && !equalPrimary) {
          return p0 > p1 ? -1 : 1;
        } else if (!twoPrimary || (twoPrimary && !equalPrimary)) {
          if (typeof p0 === 'number') {
            return -1;
          } else if (typeof p1 === 'number') {
            return 1;
          }
        }

        if (typeof t0 === 'string' && typeof t1 === 'string') {
          return t0 < t1 ? -1 : (t0 > t1 ? 1 : 0);
        } else if (typeof t0 === 'string') {
          return -1;
        } else if (typeof t1 === 'string') {
          return 1;
        }

        return 0;
      });

      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(i, this.data[i]?.doi, this.data[i]?.details,  this.data[i]?.primary);
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
    this.publicationInput = this.element.querySelector(this.options.textInputId);
    this.doiInput = this.element.querySelector(this.options.doiInputId);
    this.primaryPubCheckbox = this.element.querySelector(this.options.primaryPubCheckboxId);

    this.addButton = this.element.querySelector(this.options.addButtonId);
    this.addButton.addEventListener('click', this.#handleInput.bind(this));
    window.addEventListener('click', this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector(this.options.availabilityId);
    const publicationGroup = this.element.parentNode.querySelector(this.options.publicationGroupId);
    const publicationList = this.element.parentNode.querySelector(this.options.publicationListId);
    this.renderables = {
      none: noneAvailable,
      group: publicationGroup,
      list: publicationList,
    };

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

    const doi = strictSanitiseString(this.doiInput.value);
    const publication = strictSanitiseString(this.publicationInput.value);

    if (!this.publicationInput.checkValidity() || isNullOrUndefined(publication) || isStringEmpty(publication)) {
      window.ToastFactory.push({
        type: 'danger',
        message: 'Incorrect endorsement details provided',
        duration: this.options.notificationDuration,
      });

      this.doiInput.value = doi;
      this.publicationInput.value = publication;

      return;
    }

    const primary = Number(this.primaryPubCheckbox.checked ? this.primaryPubCheckbox.dataset.value: '0');
    const matches = parseString(doi, CLU_DOI_PATTERN);
    if (!matches?.[0]) {
      window.ToastFactory.push({
        type: 'danger',
        message: PUBLICATION_NOTIFICATIONS.InvalidDOIProvided,
        duration: this.options.notificationDuration,
      });
    }

    this.doiInput.value = '';
    this.publicationInput.value = '';
    this.primaryPubCheckbox.checked = false;
    this.data.push({
      details: publication,
      doi: matches?.[0],
      primary: primary
    });

    this.makeDirty();
    this.#redrawPublications();
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

    if (target.nodeName != 'BUTTON') {
      return;
    }

    const index = target.getAttribute(this.options.targetAttribute);
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawPublications();
    this.makeDirty();
  }
}
