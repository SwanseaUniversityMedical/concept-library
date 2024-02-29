import * as Constants from './constants.js';

/**
 * @class OntologySelectionService
 * @desc Class that allows the selection of items from arbitrary
 *       directed acyclic graphs that define taggable ontologies
 * 
 */

export default class OntologySelectionModal {
  static DataTarget = 'ontology-modal';

  constructor(element, options) {
    this.id = generateUUID();
    this.element = element;

    this.#initialise(options);
  }


  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/

  /**
   * getId
   * @desc gets the Id associated with this instance
   * @returns {string} the assoc. UUID
   */
  getId() {
    return this.id;
  }

  /**
   * isOpen
   * @desc reflects whether the dialogue is currently open
   * @returns {boolean} whether the dialogue is open
   */
  isOpen() {
    return !!this.dialogue;
  }

  /**
   * getDialogue
   * @desc get currently active dialogue, if any
   * @returns {object} the dialogue and assoc. elems/methods
   */
  getDialogue() {
    return this.dialogue;
  }


  /*************************************
   *                                   *
   *               Public              *
   *                                   *
   *************************************/
  
  /**
   * show
   * @desc shows the dialogue
   * @param {function|null} callback a callback method called once the dialogue is rendered
   * @returns {promise} a promise that resolves if the selection was confirmed, otherwise rejects
   */
  show(callback) {
    if (!isNullOrUndefined(this.dialogue)) {
      return Promise.reject();
    }

    return new Promise((resolve, reject) => {
      this.#buildDialogue();

      this.dialogue.element.addEventListener('modalUpdate', (e) => {
        this.close();

        const detail = e.detail;
        const eventType = detail.type;
        switch (eventType) {
          case Constants.EVENT_STATES.CANCELLED:
          case Constants.EVENT_STATES.CONFIRMED: {
            resolve(eventType);
          } break;

          default: {
            reject();
          } break;
        }
      });
      
      this.dialogue.show(callback);
    })
  }

  /**
   * close
   * @desc closes the dialogue if active
   * @returns {this} for chaining
   */
  close() {
    this?.dialogue?.close();
    return this;
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/

  /**
   * initialise
   * @desc Initialises the class by resolving its component templates,
   *       and handles any data initialisation
   * @param {object|null} options optional parameters
   */
  #initialise(options) {
    this.options = mergeObjects(options || { }, Constants.OPTIONS);

    const templates = { };
    const elements = this.element.querySelectorAll('template');
    for (let i = 0; i < elements.length; ++i) {
      let template = elements[i];
      let dataTarget = template.getAttribute('data-target');
      if (dataTarget !== OntologySelectionModal.DataTarget) {
        continue;
      }

      let dataName = template.getAttribute('data-name');
      if (isStringEmpty(dataName) || isStringWhitespace(dataName)) {
        continue;
      }

      templates[dataName] = Array.prototype.reduce.call(
        template.content.childNodes,
        (result, node) => result + (node.outerHTML || node.nodeValue),
        ''
      );
    }
    this.templates = templates;
  }


  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/

  /**
   * buildDialogue
   * @desc renders the top-level modal according to the options given
   * @returns {object} the dialogue object as assigned to this.dialogue
   */
  #buildDialogue() {
    this.close();

    const currentHeight = window.scrollY;
    const html = interpolateString(this.templates.modal, {
      id: this.id,
      hidden: true,
      modalSize: this.options.modalSize,
      modalTitle: this.options.modalTitle,
      modalCancel: this.options.modalCancel,
      modalConfirm: this.options.modalConfirm,
    });

    let modal = parseHTMLFromString(html);
    modal = document.body.appendChild(modal.body.children[0]);

    let buttons = modal.querySelectorAll('#target-modal-footer > button');
    buttons = Object.fromEntries([...buttons].map(elem => {
      return [elem.getAttribute('id'), elem];
    }));

    buttons.cancel.addEventListener('click', this.#handleCancel.bind(this));
    buttons.confirm.addEventListener('click', this.#handleConfirm.bind(this));

    this.dialogue = {
      // elements
      element: modal,
      buttons: buttons,
      container: modal.querySelector('#target-modal-content'),

      // dialogue methods
      show: (callback) => {
        createElement('a', { href: `#${this.id}` }).click();
        window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});

        // inform screen readers of alert
        modal.setAttribute('aria-hidden', false);
        modal.setAttribute('role', 'alert');
        modal.setAttribute('aria-live', true);

        // stop body scroll
        document.body.classList.add('modal-open');

        if (typeof(callback) === 'function') {
          callback(this.dialogue);
        }
      },
      close: () => {
        this.dialogue = null;

        document.body.classList.remove('modal-open');
        modal.remove();
        history.replaceState({ }, document.title, '#');
        window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
      },
    }

    return this.dialogue;
  }


  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/

  /**
   * handleCancel
   * @desc handles the cancel/exit btn
   * @param {event} e the assoc. event
   */
  #handleCancel(e) {
    if (!this.isOpen()) {
      return;
    }

    const event = new CustomEvent(
      'modalUpdate',
      {
        detail: {
          type: Constants.EVENT_STATES.CANCELLED,
        }
      }
    );
    this.dialogue?.element.dispatchEvent(event);
  }
  
  /**
   * handleConfirm
   * @desc handles the confirmation btn
   * @param {event} e the assoc. event
   */
  #handleConfirm(e) {
    if (!this.isOpen()) {
      return;
    }

    const event = new CustomEvent(
      'modalUpdate',
      {
        detail: {
          type: Constants.EVENT_STATES.CONFIRMED,
        }
      }
    );
    this.dialogue?.element.dispatchEvent(event);
  }
}
