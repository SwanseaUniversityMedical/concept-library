import { PUBLICATION_MIN_MSG_DURATION } from '../entityFormConstants.js';

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
    this.publicationInput = this.element.querySelector('#publication-input-box');
    this.doiInput = this.element.querySelector('#doi-input-box');
    this.addButton = this.element.querySelector('#add-input-btn');
    this.addButton.addEventListener('click', this.#handleInput.bind(this));
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
    e.preventDefault();
    e.stopPropagation();

    const publication = this.publicationInput.value;
    const doi = this.doiInput.value;
    if (!this.publicationInput.checkValidity() || isNullOrUndefined(publication) || isStringEmpty(publication)) {
      return;
    }

    const matches = parseDOI(doi);
    if (!matches?.[0]) {
      window.ToastFactory.push({
        type: 'danger',
        message: 'We couldn\'t validate the DOI you provided. Are you sure it\'s correct?',
        duration: PUBLICATION_MIN_MSG_DURATION,
      });
    }

    this.doiInput.value = '';
    this.publicationInput.value = '';
    this.data.push({
      details: publication,
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
