import { TOAST_MSG_DURATION } from '../entityFormConstants.js';

/**
 * CONTACT LIST OPTIONS
 * @desc describes the optional parameters for this class
 * 
 */
const CONTACT_LIST_OPTIONS = {
  // The minimum message duration for toast notif popups
  notificationDuration: TOAST_MSG_DURATION,

  /* Attribute name(s) */
  //  - dataAttribute: defines the attribute that's used to retrieve contextual data
  dataAttribute: 'data-field',
  //  - targetAttribute: defines the data target for individual elements which defines their index
  targetAttribute: 'data-target',

  /* Related element IDs */
  //  - textInputId: describes the text input box for contact name
  textInputId: '#publication-input-box',
  //  - emailInputId: describes the email text input box
  emailInputId: '#doi-input-box',
  //  - addButtonId: describes the 'Add' button used to add contacts
  addButtonId: '#add-input-btn',
  //  - availabilityId: describes the 'No available contacts' element
  availabilityId: '#no-available-publications',
  //  - publicationGroupId: describes the parent element of the contact list
  publicationGroupId: '#publication-group',
  //  - publicationListId: describes the contact list in which elements are held
  publicationListId: '#publication-list',
};


/**
 * CONTACT_ITEM_ELEMENT
 * @desc describes the contact item element and its interpolable targets
 * 
 */
const CONTACT_ITEM_ELEMENT = '<div class="publication-list-group__list-item" data-target="${index}"> \
  <div class="publication-list-group__list-item-names"> \
    <p> \
      ${name}${emailElement} \
    </p> \
  </div> \
  <button class="publication-list-group__list-item-btn" data-target="${index}"> \
    <span class="delete-icon"></span> \
    <span>Remove</span> \
  </button> \
</div>';


/**
 * CONTACT_EMAIL_ELEMENT
 * @desc describes the contact email element
 *       and its interpolable targets
 * 
 */
const CONTACT_EMAIL_ELEMENT = '<br/><br/><a href="mailto:{email}">${email}</a>';


/**
 * CONTACT_NOTIFICATIONS
 * @desc notification text that is used to present information
 *       to the client, _e.g._ to inform them of a validation
 *       error, or to confirm them of a forced change _etc_
 * 
 */
const CONTACT_NOTIFICATIONS = {
  // e.g. in the case of a user providing a email
  //      that isn't matched by utils.js' `CLU_EMAIL_PATTERN` regex
  InvalidEmailProvided: 'We couldn\'t validate the email you provided. Are you sure it\'s correct?',
}


/**
 * @class ContactListCreator
 * @desc A class that can be used to control publication lists
 * 
 * e.g.
 * 
  ```js
    // initialise
    const startValue = [
      { name: 'some publication title', email: 'email@email.com' },
      { name: 'some other title', email: 'email@email.com' }
    ];

    const element = document.querySelector('#publication-component');
    const creator = new ContactListCreator(element, startValue);

    // ...when retrieving data
    if (creator.isDirty()) {
      const data = creator.getData();
      
      // TODO: some save method


    }
  ```
 * 
 */
export default class ContactListCreator {
  constructor(element, data, options) {
    this.data = Array.isArray(data) ? data : [ ];
    this.dirty = false;
    this.element = element;

    // parse opts
    if (!isObjectType(options)) {
      options = { };
    }
    this.options = mergeObjects(options, CONTACT_LIST_OPTIONS);
 
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
   * @param email the contact email
   * @param {string} name the contact name
   * @returns {string} html string representing the element
   */
  #drawItem(index, email, name) {
    let emailElement;
    if (!isNullOrUndefined(email) && !isStringEmpty(email)) {
      emailElement = interpolateString(CONTACT_EMAIL_ELEMENT, { email: email });
    } else {
      emailElement = '';
    }

    return interpolateString(CONTACT_ITEM_ELEMENT, {
      index: index,
      emailElement: emailElement,
      name: name
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

      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(i, this.data[i]?.email, this.data[i]?.name);
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
    this.nameInput = this.element.querySelector(this.options.textInputId);
    this.emailInput = this.element.querySelector(this.options.emailInputId);

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

    const email = strictSanitiseString(this.emailInput.value);
    const name = strictSanitiseString(this.nameInput.value);

    if (!this.nameInput.checkValidity() || isNullOrUndefined(name) || isStringEmpty(name)) {
      window.ToastFactory.push({
        type: 'danger',
        message: 'You must provide a name for the contact',
        duration: this.options.notificationDuration,
      });

      this.emailInput.value = email;
      this.nameInput.value = name;

      return;
    }

    const matches = parseString(email.toLowerCase(), CLU_EMAIL_PATTERN);
    if (!matches?.[0]) {
      window.ToastFactory.push({
        type: 'danger',
        message: CONTACT_NOTIFICATIONS.InvalidEmailProvided,
        duration: this.options.notificationDuration,
      });
    } else {
      this.emailInput.value = '';
      this.nameInput.value = '';
      this.data.push({
        name: name,
        email: matches?.[0]
      });
  
      this.makeDirty();
      this.#redrawPublications();
    }
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
