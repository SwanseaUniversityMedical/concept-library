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
 */
export default class PublicationCreator {
  constructor(element, data) {
    this.data = data || [ ];
    this.element = element;
  
    this.#setUp();
    this.#redrawPublications();
  }

  getData() {
    return this.data;
  }

  #drawItem(index, publication) {
    return `
    <div class="publication-list-group__list-item" data-target="${index}">
      <div class="publication-list-group__list-item-url">
        <p>${publication}</p>
      </div>
      <button class="publication-list-group__list-item-btn" data-target="${index}">
        <span class="delete-icon"></span>
        <span>Remove</span>
      </button>
    </div>`
  }

  #redrawPublications() {
    this.dataResult.innerText = JSON.stringify(this.data);

    clearAllChildren(this.renderables.list, (elem) => {
      return elem.getAttribute('id') == 'pub-header';
    });
    
    if (this.data.length > 0) {
      this.renderables.list.classList.add('show');
      this.renderables.none.classList.remove('show');

      for (let i = 0; i < this.data.length; ++i) {
        const node = this.#drawItem(i, this.data[i]);
        this.renderables.list.insertAdjacentHTML('beforeend', node);
      }

      return;
    }

    this.renderables.none.classList.add('show');
    this.renderables.list.classList.remove('show');
  }

  #handleInput(e) {
    const code = e.which || e.keyCode;
    if (code != PUBLICATION_KEYCODES.ENTER) {
      return;
    }

    const input = this.element.value;
    if (isNullOrUndefined(input) || isStringEmpty(input)) {
      return;
    }
    this.element.value = '';
    this.data.push(input);
    
    this.#redrawPublications();
  }

  #handleClick(e) {
    const target = e.target;
    if (!target || !this.renderables.list.contains(target)) {
      return;
    }

    const index = target.getAttribute('data-target');
    if (isNullOrUndefined(index)) {
      return;
    }

    this.data.splice(parseInt(index), 1);
    this.#redrawPublications();
  }

  #setUp() {
    this.element.addEventListener('keyup', this.#handleInput.bind(this));
    window.addEventListener('click', this.#handleClick.bind(this));

    const noneAvailable = this.element.parentNode.querySelector('#no-available-publications');
    const publicationList = this.element.parentNode.querySelector('#publication-list');
    this.renderables = {
      none: noneAvailable,
      list: publicationList
    }

    this.dataResult = this.element.parentNode.querySelector(`[for="${this.element.getAttribute('data-field')}"]`);
  }
}
