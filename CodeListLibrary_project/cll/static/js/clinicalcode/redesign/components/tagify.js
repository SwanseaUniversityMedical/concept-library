import FuzzyQuery from "./fuzzyQuery.js";

const TAGIFY__DELAY = 1;
const TAGIFY__TIMEOUT = 10;
const TAGIFY__KEYCODES = {
  'ENTER': 13,
  'BACK': 8,
  'DOWN': 40,
  'UP': 38,
};

const TAGIFY__TAG_OPTIONS = {
  /* A predefined list of tags that can be used for autocomplete, or to control the input provided by the user */
  'items': [ ],
  /* Whether to use the value or the name keys for autocomplete and tag selected components */
  'useValue': false,
  /* Whether to perform autocomplete from a predefined list of items */
  'autocomplete': false,
  /* Whether to allow users to input duplicate tags */
  'allowDuplicates': false,
  /* Determines whether the user is restricted to the items within the predefined items list, or can input their own */
  'restricted': false,
};

/**
  * Tagify
  * @desc A class that transforms an input field into a tag component
  * @param {string/node} obj The ID of the input element or the input element itself.
  * @param {object} options An object that defines any of the optional parameters as described within TAGIFY__TAG_OPTIONS
  * @return {object} An interface to control the behaviour of the tag component.
  */
export default class Tagify {
  constructor(obj, options) {
    if (typeof obj === 'string') {
      this.id = id;
      this.element = document.getElementById(id);
    } else {
      this.element = obj;
      
      if (typeof this.element !== 'undefined') {
        this.id = this.element.getAttribute('id');
      }
    }
    this.isBackspace = false;
    this.tags = [ ];
    this.currentFocus = -1;
    
    this.#buildOptions(options || { });
    this.#initialise();
  }

  /* Adds a tag to the current list of tags */
  /** @param {string} name The name of the tag to add */
  /** @param {any} value The value of the tag to add */
  /** @return {object} Returns a tag object */
  addTag(name, value) {
    if (this.options.restricted) {
      const index = this.options.items.map(e => e.name.toLocaleLowerCase()).indexOf(name.toLocaleLowerCase());
      if (index < 0) {
        return false;
      }

      const data = this.options.items[index];
      name = data.name;
      value = data.value;
    }

    if (!this.options.allowDuplicates) {
      const index = this.tags.map(e => e.name.toLocaleLowerCase()).indexOf(name.toLocaleLowerCase());
      if (index >= 0) {
        const elem = this.tags[index].element;
        if (elem) {
          this.#wobbleElement(elem);
        }
        
        return false;
      }
    }

    const tag = this.#createTag(name, value);
    return tag;
  }
  
  /* Removes a tag from the current list of tags */
  /** @param {object} tag The tag to remove */
  removeTag(tag) {
    const name = tag.querySelector('.tag__name');
    this.tagbox.removeChild(tag);

    const index = this.tags.map(e => e.name).indexOf(name.textContent.trim());
    this.tags.splice(index, 1);

    this.#updateElement();
  }

  /* Destroys the tagify component, but not the element itself */
  destroy() {
    if (this.tagbox) {
      this.tagbox.parentNode.removeChild(this.tagbox);
    }

    delete this;
  }

  // Private methods
  #onClick(e) {
    e.preventDefault();

    if (e.target.className == 'tag__remove') {
      this.removeTag(e.target.parentNode);
    }

    this.field.focus();
  }

  #onFocusLost(e) {
    this.#deselectHighlighted();
    
    const target = e.relatedTarget;
    if (target && target.classList.contains('autocomplete-item')) {
      const name = target.getAttribute('data-name');
      this.field.value = '';
      this.addTag(name);
    }

    this.#clearAutocomplete();
    this.autocomplete.classList.remove('show');
  }

  #onKeyDown(e) {
    setTimeout(() => {
      const target = e.target;
      if (e.target.id == 'tag-field') {
        let name = target.value.trim();
        const code = e.which || e.keyCode;
        switch (code) {
          case TAGIFY__KEYCODES.ENTER: {
            if (this.currentFocus >= 0) {
              name = this.#getFocusedName();
            }
            
            if (name === '') {
              this.#deselectHighlighted();
              break;
            }
            
            target.blur();
            target.value = '';
  
            this.addTag(name);
            this.#clearAutocomplete(true);
  
            if (this.timer)
              clearTimeout(this.timer);
            
            this.timer = setTimeout(() => {
              target.focus();
            }, TAGIFY__TIMEOUT);
          } break;
  
          case TAGIFY__KEYCODES.BACK: {
            if (name === '') {
              this.#clearAutocomplete(true);
  
              if (!this.isBackspace) {
                this.#popTag();
              }
            } else {
              if (this.options.autocomplete) {
                this.#tryPopulateAutocomplete(name);
              }
            }
          } break;
  
          case TAGIFY__KEYCODES.UP:
          case TAGIFY__KEYCODES.DOWN: {
            if (this.autocomplete.classList.contains('show')) {
              e.preventDefault();
              this.currentFocus += (code == TAGIFY__KEYCODES.UP ? -1 : 1);
              this.#focusAutocompleteElement();
            }
          } break;
  
          default: {
            this.#deselectHighlighted();
  
            if (this.options.autocomplete) {
              this.#tryPopulateAutocomplete(name);
            }
  
          } break;
        }
      }

      this.isBackspace = false;
    }, TAGIFY__DELAY)
  }

  #onKeyUp(e) {

  }

  #createTag(name, value) {
    const tag = createElement('div', {
      'className': 'tag',
      'data-value': value,
      'innerHTML': `<span class="tag__name">${name}</span><button class="tag__remove" aria-label="Remove Tag ${name}">&times;</button>`
    });

    this.tagbox.insertBefore(tag, this.field);
    this.tags.push({
      'element': tag,
      'name': name,
      'value': value,
    });

    this.#updateElement();
    
    return tag;
  }

  #popTag() {
    if (this.isBackspace)
      return;
    
    this.isBackspace = true;
    if (this.tags.length <= 0)
      return;
    
    const index = this.tags.length - 1;
    const tag = this.tags[index];
    if (!tag.element.classList.contains('tag__highlighted')) {
      tag.element.classList.add('tag__highlighted');
      return;
    }

    this.tags.splice(index, 1);
    this.tagbox.removeChild(tag.element);
  }

  #deselectHighlighted() {
    if (this.field.previousSibling) {
      this.field.previousSibling.classList.remove('tag__highlighted');
    }
  }

  #bindEvents() {
    this.container.addEventListener('click', this.#onClick.bind(this), false);
    this.tagbox.addEventListener('focusout', this.#onFocusLost.bind(this), false);
    this.tagbox.addEventListener('keydown', this.#onKeyDown.bind(this), false);
    this.tagbox.addEventListener('keyup', this.#onKeyUp.bind(this), false);
  }

  #updateElement() {
    const target = this.options.useValue ? 'value' : 'name';
    this.element.value = this.tags.map(e => e[target]).join(',');
  }

  #buildOptions(options) {
    this.options = mergeObjects(options, TAGIFY__TAG_OPTIONS);
  }

  #wobbleElement(elem) {
    const method = getTransitionMethod();
    if (typeof method === 'undefined')
      return;
    
    elem.addEventListener(method, function handle(e) {
      elem.classList.remove('tag__wobble');
      elem.removeEventListener(e.type, handle, false);
    }, false);

    elem.classList.add('tag__wobble');
  }

  #clearAutocomplete(hide) {
    this.currentFocus = -1;

    while (this.autocomplete.lastElementChild) {
      this.autocomplete.removeChild(this.autocomplete.lastElementChild);
    }

    if (hide) {
      this.autocomplete.classList.remove('show');
    }
  }

  #getFocusedName() {
    const children = this.autocomplete.children;
    if (this.currentFocus < children.length) {
      return children[this.currentFocus].getAttribute('data-name');
    }

    return '';
  }

  #popFocusedElement() {
    const children = this.autocomplete.children;
    for (let i = 0; i < children.length; ++i) {
      children[i].classList.remove('autocomplete-item__highlighted');
    }
  }
  
  #focusAutocompleteElement() {
    this.#popFocusedElement();
    
    const children = this.autocomplete.children;
    const childLength = children.length;
    this.currentFocus = this.currentFocus < 0 ? (childLength - 1) : (this.currentFocus >= childLength ? 0 : this.currentFocus);

    if (this.currentFocus < childLength) {
      const element = children[this.currentFocus];
      element.classList.add('autocomplete-item__highlighted');

      this.autocomplete.scrollTop = element.offsetTop;
    }
  }

  #generateAutocompleteElements(results) {
    for (let i = 0; i < results.length; ++i) {
      const data = results[i];
      const item = createElement('button', {
        'className': 'autocomplete-item',
        'data-value': data.value,
        'data-name': data.name,
      });

      const text = createElement('span', {
        'className': 'autocomplete-item__title',
        'innerHTML': data.name,
      });

      item.appendChild(text);
      this.autocomplete.appendChild(item);
    }
  }

  #tryPopulateAutocomplete(value) {
    if (value === '' || this.options.items.length <= 0) {
      this.#clearAutocomplete(true);
      return;
    }

    if (!this.haystack) {
      this.haystack = this.options.items.map(e => e.name);
    }
    
    let results = FuzzyQuery.Search(this.haystack, value, FuzzyQuery.Results.SORT, FuzzyQuery.Transformers.IgnoreCase);
    results.sort((a, b) => {
      if (a.score === b.score) {
        return 0;
      } else if (a.score > b.score) {
        return 1;
      } else if (a.score < b.score) {
        return -1;
      }
    });

    results = results.map((e) => {
      const item = this.options.items.find(x => x.name.toLocaleLowerCase() === e.item.toLocaleLowerCase());
      return item;
    });
    
    if (results.length > 0) {
      this.#clearAutocomplete(false);
      this.autocomplete.classList.add('show');
      this.#generateAutocompleteElements(results);

      return;
    }

    this.#clearAutocomplete(true);
  }

  #initialise() {
    this.container = createElement('div', {
      'className': 'tags-root-container',
    });

    this.tagbox = createElement('div', {
      'className': 'tags-container',
    });

    this.autocomplete = createElement('div', {
      'className': 'tags-autocomplete-container filter-scrollbar',
    });

    this.field = createElement('input', {
      'type': 'text',
      'className': 'tags-input-field',
      'id': 'tag-field',
      'placeholder': this.element.placeholder || '',
    });

    this.tagbox.appendChild(this.field);
    this.container.appendChild(this.tagbox);
    this.container.appendChild(this.autocomplete);
    this.element.type = 'hidden';
    this.element.parentNode.insertBefore(this.container, this.element.nextSibling);

    this.#bindEvents();
  }
}
