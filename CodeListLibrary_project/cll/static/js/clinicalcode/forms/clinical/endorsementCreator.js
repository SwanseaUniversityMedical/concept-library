/**
 * endorsement_OPTIONS
 * @desc describes the optional parameters for this class
 *
 */
const endorsement_OPTIONS = {
  // The minimum message duration for toast notif popups
  notificationDuration: 5000,

  /* Attribute name(s) */
  //  - dataAttribute: defines the attribute that's used to retrieve contextual data
  dataAttribute: "data-field",
  //  - targetAttribute: defines the data target for individual elements which defines their index
  targetAttribute: "data-target",

  /* Related element IDs */
  //  - textInputId: describes the text input box for endorsement details
  textInputId: "#endorsement-input-box",
  //  - addButtonId: describes the 'Add' button used to add endorsements
  addButtonId: "#add-input-btn",
  //  - availabilityId: describes the 'No available endorsements' element
  availabilityId: "#no-available-endorsements",
  //  - endorsementGroupId: describes the parent element of the endorsement list
  endorsementGroupId: "#endorsement-group",
  //  - endorsementListId: describes the endorsement list in which elements are held
  endorsementListId: "#endorsement-list",

  endorsementDatepickerId: "#entity-endorsements-input",
};
import {
  ENTITY_HANDLERS,
} from "../entityCreator/utils.js";

import {
  ENTITY_ACCEPTABLE_DATE_FORMAT
} from '../entityFormConstants.js';

/**
 * endorsement_ITEM_ELEMENT
 * @desc describes the endorsement item element and its interpolable targets
 *
 */
const endorsement_ITEM_ELEMENT =
  '<div class="publication-list-group__list-item" data-target="${index}" style="display: flex; justify-content: space-between; align-items: center;"> \
  <div class="publication-list-group__list-item-url" style="flex: 1;">\
    <p style="margin: 0;">${date}</p> \
  </div>\
  <div class="publication-list-group__list-item-date" style="flex: 1; text-align: center;">\
    <p style="margin: 0;">${endorsement_organisation}</p> \
  </div>\
  <button class="publication-list-group__list-item-btn" data-target="${index}" style="margin-left: 10px;"> \
    <span class="delete-icon"></span> \
    <span>Remove</span> \
  </button> \
</div>';

/**
 * @class endorsementCreator
 * @desc A class that can be used to control endorsement lists
 * 
 * e.g.
 * 
  ```js
    // initialise
    const startValue = [
      { endorsement_organisation: 'some other title' }
    ];

    const element = document.querySelector('#endorsement-component');
    const creator = new endorsementCreator(element, startValue);

    // ...when retrieving data
    if (creator.isDirty()) {
      const data = creator.getData();
      
      // TODO: some save method


    }
  ```
 * 
 */
export default class endorsementCreator {
  constructor(element, data, options) {
    this.data = Array.isArray(data) ? data : [];
    this.dirty = false;
    this.element = element;

    // parse opts
    if (!isObjectType(options)) {
      options = {};
    }
    this.options = mergeObjects(options, endorsement_OPTIONS);

    // init
    this.#setUp();
    this.#redrawendorsements();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getData
   * @returns {object} the endorsement data
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
   * @param {integer} index the index of the endorsement in our data
   * @param {string} endorsement the endorsement name
   * @returns {string} html string representing the element
   */
  #drawItem(index, endorsement_organisation,date) {

    return interpolateString(endorsement_ITEM_ELEMENT, {
      index: index,
      date: date,
      endorsement_organisation: endorsement_organisation
    });
  }

  /**
   * redrawendorsements
   * @desc redraws the entire endorsement list
   */
  #redrawendorsements() {
    this.dataResult.innerText = JSON.stringify(this.data);
    this.renderables.list.innerHTML = "";

    if (this.data.length > 0) {
      this.renderables.group.classList.add("show");
      this.renderables.none.classList.remove("show");
      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(
          i,
          this.data[i]?.date,
          this.data[i]?.endorsement_organisation
        );
        this.renderables.list.insertAdjacentHTML("beforeend", node);
      }

      return;
    }

    this.renderables.none.classList.add("show");
    this.renderables.group.classList.remove("show");
  }

  /**
   * setUp
   * @desc initialises the endorsement component
   */
  #setUp() {
    this.endorsementInput = this.element.querySelector(this.options.textInputId);

    this.datepicker = ENTITY_HANDLERS['datepicker'](this.element.querySelector(this.options.endorsementDatepickerId), [])

    let initialDate = moment(this.element.querySelector(this.options.endorsementDatepickerId).getAttribute('data-value'), ENTITY_ACCEPTABLE_DATE_FORMAT);
    initialDate = initialDate.isValid() ? initialDate : moment();
    initialDate = initialDate.format('DD/MM/YYYY');
    this.datepicker.setDate(initialDate,true);

    this.element.querySelector(this.options.endorsementDatepickerId).setAttribute('data-value',initialDate);


    this.addButton = this.element.querySelector(this.options.addButtonId);
    this.addButton.addEventListener("click", this.#handleInput.bind(this));
    window.addEventListener("click", this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector(
      this.options.availabilityId
    );
    const endorsementGroup = this.element.parentNode.querySelector(
      this.options.endorsementGroupId
    );
    const endorsementList = this.element.parentNode.querySelector(
      this.options.endorsementListId
    );
    this.renderables = {
      none: noneAvailable,
      group: endorsementGroup,
      list: endorsementList,
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
   * @desc bindable event handler for key up events of the endorsement input box
   * @param {event} e the event of the input
   */
  #handleInput(e) {
    e.preventDefault();
    e.stopPropagation();

    const endorsement = this.endorsementInput.value;
    const date = this.element.querySelector(this.options.endorsementDatepickerId);

    
    if (!this.endorsementInput.checkValidity() || isNullOrUndefined(endorsement) || isStringEmpty(endorsement)) {
      window.ToastFactory.push({
        type: 'danger',
        message: "Incorrect endorsement details provided",
        duration: this.options.notificationDuration,
      });
      return;
    }

    if (!date.getAttribute('data-value')) {
      return;
    }

    this.endorsementInput.value = "";
    let filteredDate = moment(date.getAttribute('data-value'), ENTITY_ACCEPTABLE_DATE_FORMAT);
    filteredDate = filteredDate.isValid() ? filteredDate : moment();
    filteredDate = filteredDate.format('DD/MM/YYYY');
    this.element.querySelector(this.options.endorsementDatepickerId).setAttribute('data-value',filteredDate);
    
    this.data.push({ endorsement_organisation: endorsement, date: date.getAttribute('data-value')});
    this.makeDirty();

    this.#redrawendorsements();
  }

  /**
   * handleClick
   * @desc bindable event handler for click events of the endorsement item's delete button
   * @param {event} e the event of the input
   */
  #handleClick(e) {
    const target = e.target;
    if (!target || !this.renderables.list.contains(target)) {
      return;
    }

    if (target.nodeName != "BUTTON") {
      return;
    }

    const index = target.getAttribute(this.options.targetAttribute);
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawendorsements();
    this.makeDirty();
  }
}
