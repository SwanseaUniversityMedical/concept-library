/**
 * Class wrapping & managing an autocomplete component
 * 
 * @note can be combined with `components/fuzzyQuery.js` for FTS
 * 
 * @example
 *  const options = [{ id: 1, term: 'hello' }, { id: 2, term: 'world' }];
 * 
 *  const element = new Autocomplete({
 *    rootNode: document.querySelector('.autocomplete-container'),
 *    inputNode: document.querySelector('.autocomplete-input'),
 *    resultsNode: document.querySelector('.autocomplete-results'),
 *    searchFn: (input) => {
 *      if (input.length <= 3) {
 *        return [];
 *      }
 *  
 *      return options.filter(x => x.term.toLocaleLowerCase().startsWith(input.toLocaleLowerCase()));
 *    },
 *  });
 * 
 * @class
 * @constructor
 */
export class Autocomplete {
  /**
   * @desc
   * @type {Array<Function>}
   * @private
   */
  #disposables = [];

  /**
   * @param {object}      param0                          constructor args
   * @param {HTMLElement} param0.rootNode                 the autocomplete component container element
   * @param {HTMLElement} param0.inputNode                the autocomplete text input element
   * @param {HTMLElement} param0.resultsNode              the autocomplete results dropdown container element
   * @param {Function}    param0.searchFn                 a function to evaluate the search term, returning an array matching the specified input query
   * @param {boolean}     [param0.shouldAutoSelect=false] optionally specify whether to automatically select the element; defaults to `false`
   * @param {Function}    [param0.onShow=Function]        optionally specify a function to be called when the results are shown; defaults to a nullable callable
   * @param {Function}    [param0.onHide=Function]        optionally specify a function to be called when the results are hidden; defaults to a nullable callable
   */
  constructor({
    rootNode,
    inputNode,
    resultsNode,
    searchFn,
    shouldAutoSelect = false,
    onShow = () => {},
    onHide = () => {},
  }) {
    this.rootNode = rootNode;
    this.inputNode = inputNode;
    this.resultsNode = resultsNode;
    this.searchFn = searchFn;
    this.shouldAutoSelect = shouldAutoSelect;
    this.onShow = onShow;
    this.onHide = onHide;
    this.activeIndex = -1;
    this.resultsCount = 0;
    this.showResults = false;
    this.hasInlineAutocomplete = this.inputNode.getAttribute('aria-autocomplete') === 'both';

    // Setup events
    const focusHnd = this.#handleFocus.bind(this);
    const keyUpHnd = this.#handleKeyup.bind(this);
    const keyDownHnd = this.#handleKeydown.bind(this);
    const resClickHnd = this.#handleResultClick.bind(this);
    const docClickHnd = this.#handleDocumentClick.bind(this);
    document.body.addEventListener('click', docClickHnd);
    this.resultsNode.addEventListener('click', resClickHnd);
    this.inputNode.addEventListener('focus', focusHnd);
    this.inputNode.addEventListener('keyup', keyUpHnd);
    this.inputNode.addEventListener('keydown', keyDownHnd);

    // Cleanup
    this.#disposables.push(() => {
      document.body.removeEventListener('click', docClickHnd);
      this.resultsNode.removeEventListener('click', resClickHnd);
      this.inputNode.removeEventListener('focus', focusHnd);
      this.inputNode.removeEventListener('keyup', keyUpHnd);
      this.inputNode.removeEventListener('keydown', keyDownHnd);
    });
  }


  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/

  getItemAt(index) {
    return this.resultsNode.querySelector(`#autocomplete-result-${index}`);
  }

  selectItem(node) {
    if (node) {
      this.inputNode.value = node.innerText;
      this.hideResults();
    }
  }

  checkSelection() {
    if (this.activeIndex < 0) {
      return;
    }

    const activeItem = this.getItemAt(this.activeIndex);
    this.selectItem(activeItem);
  }

  autocompleteItem() {
    const autocompletedItem = this.resultsNode.querySelector('.selected');
    const input = this.inputNode.value;
    if (!autocompletedItem || !input) {
      return;
    }

    const autocomplete = autocompletedItem.innerText;
    if (input !== autocomplete) {
      this.inputNode.value = autocomplete;
      this.inputNode.setSelectionRange(input.length, autocomplete.length);
    }
  }

  updateResults() {
    const input = this.inputNode.value;
    const results = this.searchFn(input);
    this.hideResults();

    if (results.length === 0) {
      return;
    }

    this.resultsNode.innerHTML = results.map((result, index) => {
      const isSelected = this.shouldAutoSelect && index === 0;
      if (isSelected) {
        this.activeIndex = 0;
      }

      return `
        <li
          id='autocomplete-result-${index}'
          class='autocomplete-result${isSelected ? ' selected' : ''}'
          role='option'
          ${isSelected ? "aria-selected='true'" : ''}
        >
          ${result}
        </li>
      `;
    }).join('');

    this.resultsNode.classList.remove('hidden');
    this.rootNode.setAttribute('aria-expanded', true);
    this.resultsCount = results.length;
    this.shown = true;
    this.onShow();
  }

  hideResults() {
    this.shown = false;
    this.activeIndex = -1;
    this.resultsCount = 0;

    this.resultsNode.innerHTML = '';
    this.resultsNode.classList.add('hidden');
    this.rootNode.setAttribute('aria-expanded', 'false');
    this.inputNode.setAttribute('aria-activedescendant', '');

    this.onHide();
  }

  dispose() {
    let disposable;
    for (let i = this.#disposables.length; i > 0; i--) {
      disposable = this.#disposables.pop();
      if (typeof disposable !== 'function') {
        continue;
      }

      disposable();
    }
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #handleDocumentClick(event) {
    if (event.target === this.inputNode || this.rootNode.contains(event.target)) {
      return;
    }

    this.hideResults();
  }

  #handleKeyup(event) {
    const { key } = event
    switch (key) {
      case 'ArrowUp':
      case 'ArrowDown':
      case 'Escape':
      case 'Enter':
        event.preventDefault();
        return;

      default:
        this.updateResults();
    }

    if (!this.hasInlineAutocomplete || key === 'Backspace') {
      return;
    }

    this.autocompleteItem();
  }

  #handleKeydown(event) {
    const { key } = event;
    let activeIndex = this.activeIndex;

    if (key === 'Escape') {
      this.hideResults();
      this.inputNode.value = '';
      return;
    }

    if (this.resultsCount < 1) {
      if (!this.hasInlineAutocomplete || (key !== 'ArrowDown' & key !== 'ArrowUp')) {
        return;
      }

      this.updateResults();
    }

    let activeItem;
    const prevActive = this.getItemAt(activeIndex);
    switch(key) {
      case 'ArrowUp':
        if (activeIndex <= 0) {
          activeIndex = this.resultsCount - 1;
        } else {
          activeIndex -= 1;
        }
        break;

      case 'ArrowDown':
        if (activeIndex === -1 || activeIndex >= this.resultsCount - 1) {
          activeIndex = 0;
        } else {
          activeIndex += 1;
        }
        break;

      case 'Enter':
        activeItem = this.getItemAt(activeIndex);
        this.selectItem(activeItem);
        return;

      case 'Tab':
        this.checkSelection();
        this.hideResults();
        return;

      default:
        return;
    }

    event.preventDefault();
    activeItem = this.getItemAt(activeIndex);
    this.activeIndex = activeIndex;

    if (prevActive) {
      prevActive.classList.remove('selected');
      prevActive.setAttribute('aria-selected', 'false');
    }

    if (activeItem) {
      this.inputNode.setAttribute('aria-activedescendant', `autocomplete-result-${activeIndex}`);
      activeItem.classList.add('selected');
      activeItem.setAttribute('aria-selected', 'true');

      if (this.hasInlineAutocomplete) {
        this.inputNode.value = activeItem.innerText;
      }
    } else {
      this.inputNode.setAttribute('aria-activedescendant', '');
    }
  }

  #handleFocus(event) {
    this.updateResults();
  }

  #handleResultClick(event) {
    if (event.target && event.target.nodeName === 'LI') {
      this.selectItem(event.target);
    }
  }
};
