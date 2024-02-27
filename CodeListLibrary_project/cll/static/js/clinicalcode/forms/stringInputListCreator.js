/**
 * StringInputListCreator
 * @desc A class that can be used to control input lists
 * 
 * e.g.
 * 
 * const startValue = ['item 1', 'item 2'];
 * const element = document.querySelector('#publication-component');
 * const creator = new StringInputListCreator(element, startValue);
 * 
 */
export default class StringInputListCreator {
  constructor(element, data) {
    this.data = data || [ ];
    this.element = element;
    this.dirty = false;
 
    this.#setUp();
    this.#redrawElements();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getData
   * @returns {object} the list data
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
   * @param {integer} index the index of the list in our data
   * @param {string} listItem the list item name 
   * @returns {string} html string representing the element
   */
  #drawItem(index, listItem) {
    return `
    <div class="publication-list-group__list-item" data-target="${index}">
      <div class="publication-list-group__list-item-url">
        <p>${listItem}</p>
      </div>
      <button class="publication-list-group__list-item-btn" data-target="${index}">
        <span class="delete-icon"></span>
        <span>Remove</span>
      </button>
    </div>`
  }

  /**
   * redrawElements
   * @desc redraws the entire list
   */
  #redrawElements() {
    this.dataResult.innerText = JSON.stringify(this.data);
    this.renderables.list.innerHTML = '';
    
    if (this.data.length > 0) {
      this.renderables.group.classList.add('show');
      this.renderables.none.classList.remove('show');

      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(i, this.data[i]);
        this.renderables.list.insertAdjacentHTML('beforeend', node);
      }

      return;
    }

    this.renderables.none.classList.add('show');
    this.renderables.group.classList.remove('show');
  }

  /**
   * setUp
   * @desc initialises the list component
   */
  #setUp() {
    this.listInput = this.element.querySelector('.publication-list-group__interface-children > .text-input');
    this.addButton = this.element.querySelector('#add-input-btn');
    this.addButton.addEventListener('click', this.#handleInput.bind(this));
    window.addEventListener('click', this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector('#no-available-publications');
    const listGroup = this.element.parentNode.querySelector('#publication-group');
    const list = this.element.parentNode.querySelector('#publication-list');
    this.renderables = {
      none: noneAvailable,
      group: listGroup,
      list: list,
    }

    this.dataResult = this.element.parentNode.querySelector(`[for="${this.element.getAttribute('data-field')}"]`);
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/
  /**
   * handleInput
   * @desc bindable event handler for key up events of the list input box
   * @param {event} e the event of the input 
   */
  #handleInput(e) {
    e.preventDefault();
    e.stopPropagation();

    const listItem = this.listInput.value;
    if (!this.listInput.checkValidity() || isNullOrUndefined(listItem) || isStringEmpty(listItem)) {
      return;
    }

    this.listInput.value = '';
    this.data.push(listItem);
    this.makeDirty();
    
    this.#redrawElements();
  }

  /**
   * handleClick
   * @desc bindable event handler for click events of the list item's delete button
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

    const index = target.getAttribute('data-target');
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawElements();
    this.makeDirty();
  }
}
