/**
 * endorsment_OPTIONS
 * @desc describes the optional parameters for this class
 *
 */
const endorsment_OPTIONS = {
  // The minimum message duration for toast notif popups
  notificationDuration: 5000,

  /* Attribute name(s) */
  //  - dataAttribute: defines the attribute that's used to retrieve contextual data
  dataAttribute: "data-field",
  //  - targetAttribute: defines the data target for individual elements which defines their index
  targetAttribute: "data-target",

  /* Related element IDs */
  //  - textInputId: describes the text input box for endorsment details
  textInputId: "#endorsment-input-box",
  //  - addButtonId: describes the 'Add' button used to add endorsments
  addButtonId: "#add-input-btn",
  //  - availabilityId: describes the 'No available endorsments' element
  availabilityId: "#no-available-endorsments",
  //  - endorsmentGroupId: describes the parent element of the endorsment list
  endorsmentGroupId: "#endorsment-group",
  //  - endorsmentListId: describes the endorsment list in which elements are held
  endorsmentListId: "#endorsment-list",

  endorsmentDatepickerId: "#entity-endorsments-input",
};
import {
  ENTITY_HANDLERS,
} from "../entityCreator/utils.js";
/**
 * endorsment_ITEM_ELEMENT
 * @desc describes the endorsment item element and its interpolable targets
 *
 */
const endorsment_ITEM_ELEMENT =
  '<div class="publication-list-group__list-item" data-target="${index}"> \
  <div class="publication-list-group__list-item-url"> \
    <p>${endorsment} - ${date}</p> \
  </div> \
  <button class="publication-list-group__list-item-btn" data-target="${index}"> \
    <span class="delete-icon"></span> \
    <span>Remove</span> \
  </button> \
</div>';

/**
 * @class endorsmentCreator
 * @desc A class that can be used to control endorsment lists
 * 
 * e.g.
 * 
  ```js
    // initialise
    const startValue = [
      { details: 'some other title' }
    ];

    const element = document.querySelector('#endorsment-component');
    const creator = new endorsmentCreator(element, startValue);

    // ...when retrieving data
    if (creator.isDirty()) {
      const data = creator.getData();
      
      // TODO: some save method


    }
  ```
 * 
 */
export default class endorsmentCreator {
  constructor(element, data, options) {
    this.data = Array.isArray(data) ? data : [];
    this.dirty = false;
    this.element = element;

    // parse opts
    if (!isObjectType(options)) {
      options = {};
    }
    this.options = mergeObjects(options, endorsment_OPTIONS);

    // init
    this.#setUp();
    this.#redrawendorsments();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getData
   * @returns {object} the endorsment data
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
   * @param {integer} index the index of the endorsment in our data
   * @param {string} endorsment the endorsment name
   * @returns {string} html string representing the element
   */
  #drawItem(index, endorsment) {
    return interpolateString(endorsment_ITEM_ELEMENT, {
      index: index,
      endorsment: endorsment,
    });
  }

  /**
   * redrawendorsments
   * @desc redraws the entire endorsment list
   */
  #redrawendorsments() {
    this.dataResult.innerText = JSON.stringify(this.data);
    this.renderables.list.innerHTML = "";

    if (this.data.length > 0) {
      this.renderables.group.classList.add("show");
      this.renderables.none.classList.remove("show");
        console.log(this.data);
      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(
          i,
          this.data[i]?.details
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
   * @desc initialises the endorsment component
   */
  #setUp() {
    this.endorsmentInput = this.element.querySelector(this.options.textInputId);

    const datepicker = ENTITY_HANDLERS['datepicker'](this.element.querySelector(this.options.endorsmentDatepickerId), [])

    this.addButton = this.element.querySelector(this.options.addButtonId);
    this.addButton.addEventListener("click", this.#handleInput.bind(this));
    window.addEventListener("click", this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector(
      this.options.availabilityId
    );
    const endorsmentGroup = this.element.parentNode.querySelector(
      this.options.endorsmentGroupId
    );
    const endorsmentList = this.element.parentNode.querySelector(
      this.options.endorsmentListId
    );
    this.renderables = {
      none: noneAvailable,
      group: endorsmentGroup,
      list: endorsmentList,
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
   * @desc bindable event handler for key up events of the endorsment input box
   * @param {event} e the event of the input
   */
  #handleInput(e) {
    e.preventDefault();
    e.stopPropagation();

    const endorsment = this.endorsmentInput.value;

    this.endorsmentInput.value = "";
    this.data.push({ details: endorsment });
    this.makeDirty();

    this.#redrawendorsments();
  }

  /**
   * handleClick
   * @desc bindable event handler for click events of the endorsment item's delete button
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
    this.#redrawendorsments();
    this.makeDirty();
  }
}
