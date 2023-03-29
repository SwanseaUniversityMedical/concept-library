/**
 * PUBLICATION_KEYCODES
 * @desc Keycodes used by publication creator
 */
const PUBLICATION_KEYCODES = {
  // Add publication
  ENTER: 13,
}

/**
 * PublicationCreator
 * @desc A class that can be used to control publication lists
 * 
 * e.g.
 * 
 * const startValue = ['Publication 1', 'Publication 2'];
 * const element = document.querySelector('#publication-component');
 * const creator = new PublicationCreator(element, startValue);
 * 
 */
export default class PublicationCreator {
  constructor(element, data) {
    this.data = data || [ ];
    this.element = element;
    this.dirty = false;
  
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
   * @param {integer} index the index of the publication in our data
   * @param {string} publication the publication name 
   * @returns {string} html string representing the element
   */
  #drawItem(index, doi, publication) {
    const interp = (!isNullOrUndefined(doi) && !isStringEmpty(doi)) ? `<br/><br/><a href="https://doi.org/${doi}">${doi}</a>` : '';
    return `
    <div class="publication-list-group__list-item" data-target="${index}">
      <div class="publication-list-group__list-item-url">
        <p>${publication}${interp}</p>
      </div>
      <button class="publication-list-group__list-item-btn" data-target="${index}">
        <span class="delete-icon"></span>
        <span>Remove</span>
      </button>
    </div>`
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
        const node = this.#drawItem(i, this.data[i]?.doi, this.data[i]?.details);
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
    this.element.addEventListener('keyup', this.#handleInput.bind(this));
    window.addEventListener('click', this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector('#no-available-publications');
    const publicationGroup = this.element.parentNode.querySelector('#publication-group');
    const publicationList = this.element.parentNode.querySelector('#publication-list');
    this.renderables = {
      none: noneAvailable,
      group: publicationGroup,
      list: publicationList,
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
   * @desc bindable event handler for key up events of the publication input box
   * @param {event} e the event of the input 
   */
  #handleInput(e) {
    const code = e.keyIdentifier || e.which || e.keyCode;
    if (code != PUBLICATION_KEYCODES.ENTER) {
      return;
    }

    e.preventDefault();
    e.stopPropagation();

    const input = this.element.value;
    if (!e.target.checkValidity() || isNullOrUndefined(input) || isStringEmpty(input)) {
      return;
    }

    const matches = parseDOI(input);
    this.element.value = '';
    this.data.push({
      details: input,
      doi: matches?.[0],
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

    const index = target.getAttribute('data-target');
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawPublications();
    this.makeDirty();
  }
}
