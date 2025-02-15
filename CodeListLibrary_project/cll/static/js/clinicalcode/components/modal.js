/**
 * PROMPT_BUTTON_TYPES
 * @desc Defines the enums for the button types (i.e., whether to resolve or reject on button click)
 */
const PROMPT_BUTTON_TYPES = {
  REJECT: 0,
  CONFIRM: 1,
};

/**
 * PROMPT_BUTTONS_DEFAULT
 * @desc Defines the default type and html of the buttons
 */
const PROMPT_BUTTONS_DEFAULT = [
  {
    name: 'Confirm',
    type: PROMPT_BUTTON_TYPES.CONFIRM,
    html: `<button class="primary-btn text-accent-darkest bold secondary-accent" id="confirm-button"></button>`,
  },
  {
    name: 'Cancel',
    type: PROMPT_BUTTON_TYPES.REJECT,
    html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="reject-button"></button>`,
  },
];

/**
 * PROMPT_DEFAULT_CONTAINER
 * @desc Defines the default style of the modal container
 */
const PROMPT_DEFAULT_CONTAINER = '\
<div class="target-modal target-modal-${size}" id="${id}" aria-hidden="true"> \
  <div class="target-modal__container"> \
    <div class="target-modal__header"> \
      <h2 id="target-modal-title">${title}</h2> \
      <a href="#" class="target-modal__header-close" aria-label="Close Modal" id="modal-close-btn"></a> \
    </div> \
    <div class="target-modal__body target-modal__body--constrained" id="target-modal-content"> \
      ${content} \
    </div> \
  </div> \
</div>';

/**
 * PROMPT_MODAL_SIZES
 * @desc Defines the sizes available for the modal prompt
 */
const PROMPT_MODAL_SIZES = {
  Small: 'sm',
  Medium: 'md',
  Large: 'lg',
};

/**
 * PROMPT_DEFAULT_PARAMS
 * @desc Defines the default parameters for the modal
 */
const PROMPT_DEFAULT_PARAMS = {
  id: 'modal-dialog',
  title: 'Modal',
  content: '',
  showFooter: true,
  size: PROMPT_MODAL_SIZES.Medium,
  buttons: PROMPT_BUTTONS_DEFAULT,
  onRender: () => { },
  beforeAccept: () => { },
};

/**
 * @class CancellablePromise
 * @desc Creates an instance of a promise that can be cancelled
 * 
 * e.g.
  ```js
    const promise = new CancellablePromise((resolve, reject) => {
      // do something
    });

    // e.g. after n seconds
    promise.cancel();
  ```
 * 
 */
class CancellablePromise {
  constructor(executor) {
    let _reject = null;
    const cancellablePromise = new Promise((resolve, reject) => {
      _reject = reject;
      return executor(resolve, reject);
    });
    cancellablePromise.cancel = _reject;

    return cancellablePromise;
  }
};

/**
 * @class ModalResult
 * @desc Creates an instance that is passed as a parameter when resolved/rejected via closure / button interaction
 * 
 */
class ModalResult {
  constructor(name, type, data) {
    this.name = name;
    this.type = type;
    this.data = data;
  }
};

/**
 * @class ModalFactory
 * @desc A window-level instance to create modals
 * 
 * e.g.
  ```js
    const ModalFactory = window.ModalFactory;
    ModalFactory.create({
      id: 'test-dialog',
      title: 'Hello',
      content: '<p>Hello</p>',
      buttons: [
        {
          name: 'Cancel',
          type: ModalFactory.ButtonTypes.REJECT,
          html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="cancel-button"></button>`,
        },
        {
          name: 'Reject',
          type: ModalFactory.ButtonTypes.REJECT,
          html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="reject-button"></button>`,
        },
        {
          name: 'Confirm',
          type: ModalFactory.ButtonTypes.CONFIRM,
          html: `<button class="primary-btn text-accent-darkest bold secondary-accent" id="confirm-button"></button>`,
        },
        {
          name: 'Accept',
          type: ModalFactory.ButtonTypes.CONFIRM,
          html: `<button class="primary-btn text-accent-darkest bold secondary-accent" id="accept-button"></button>`,
        },
      ]
    })
    .then((result) => {
      // e.g. user pressed a button that has type=ModalFactory.ButtonTypes.CONFIRM
      const name = result.name;
      if (name == 'Confirm') {
        console.log('[success] user confirmed', result);
      } else if (name == 'Accept') {
        console.log('[success] user accepted', result);
      }
    })
    .catch((result) => {
      // An error occurred somewhere (unrelated to button input)
      if (!(result instanceof ModalFactory.ModalResults)) {
        return console.error(result);
      }

      // e.g. user pressed a button that has type=ModalFactory.ButtonTypes.REJECT
      const name = result.name;
      if (name == 'Cancel') {
        console.log('[failure] user cancelled', result);
      } else if (name == 'Reject') {
        console.log('[failure] rejected', result);
      }
    });
  ```
 * 
 */
class ModalFactory {
  ButtonTypes = PROMPT_BUTTON_TYPES;
  DefaultButtons = PROMPT_BUTTONS_DEFAULT;
  ModalSizes = PROMPT_MODAL_SIZES;
  ModalResults = ModalResult;

  constructor() {
    this.modal = null;
  }

  /**
   * create
   * @desc instantiates a modal, given a set of options that
   *       relate to this instance
   * 
   * @param {object|null} options the options associated with this
   *                              instance, see `PROMPT_DEFAULT_PARAMS`
   *                              for more details
   * 
   * @returns {object<Promise>} that will resolve or reject after
   *                            either (a) button-related actions;
   *                            or (b) due to an error occurring
   * 
   */
  create(options) {
    options = options || { };
    this.closeCurrentModal();

    try {
      options = mergeObjects(options, PROMPT_DEFAULT_PARAMS);

      const { id, title, content, showFooter, buttons, size } = options;
    
      const html = interpolateString(PROMPT_DEFAULT_CONTAINER, { id: id, title: title, content: content, size: size });
      const doc = parseHTMLFromString(html, true);
      const currentHeight = window.scrollY;
      const modal = document.body.appendChild(doc.body.children[0]);
      const container = modal.querySelector('.target-modal__container');

      let footer;
      if (showFooter) {
        footer = createElement('div', {
          class: 'target-modal__footer',
          id: 'target-modal-footer',
        });

        footer = container.appendChild(footer);
      }

      const footerButtons = [ ];
      if (!isNullOrUndefined(footer)) {
        for (let i = 0; i < buttons.length; ++i) {
          let button = buttons[i];
          let item = parseHTMLFromString(button.html, true);
          item = footer.appendChild(item.body.children[0]);
          item.innerText = button.name;
          item.setAttribute('aria-label', button.name);
  
          footerButtons.push({
            name: button.name,
            type: button.type,
            element: item,
          });
        }
      }

      const closeModal = (method, details) => {
        document.body.classList.remove('modal-open');
        window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
        modal.remove();
        history.pushState("", document.title, window.location.pathname + window.location.search);
        this.modal = null;

        if (!method) {
          return;
        }

        if (details) {
          method(new ModalResult(details?.name || 'Cancel', details?.type || this.ButtonTypes.REJECT, details?.data || null));
        } else {
          method(new ModalResult('Cancel', this.ButtonTypes.REJECT));
        }
      };

      const promise = new CancellablePromise((resolve, reject) => {
        for (let i = 0; i < footerButtons.length; ++i) {
          let btn = footerButtons[i];
          btn.element.addEventListener('click', (e) => {
            switch (btn.type) {
              case this.ButtonTypes.CONFIRM: {
                let data;
                if (options.beforeAccept) {
                  data = options.beforeAccept(modal);
                }
                
                closeModal(resolve, Object.assign({}, btn, { data: data }));
              } break;

              case this.ButtonTypes.REJECT:
              default: {
                closeModal(reject, btn);
              } break;
            }
          });
        }

        const exit = modal.querySelector('#modal-close-btn');
        if (exit) {
          exit.addEventListener('click', (e) => {
            e.preventDefault();
            closeModal(reject);
          });
        }
        
        // Show the modal
        createElement('a', { href: `#${id}` }).click();
        window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
    
        // Inform screen readers of alert
        modal.setAttribute('aria-hidden', false);
        modal.setAttribute('role', 'alert');
        modal.setAttribute('aria-live', true);

        // Stop scrolling on body when modal is open
        document.body.classList.add('modal-open');

        if (options.onRender) {
          options.onRender(modal);
        }
      });

      this.modal = {
        element: modal,
        promise: promise,
        close: closeModal,
      };

      return promise;
    }
    catch (e) {
      return Promise.reject(e)
    }
  }

  /**
   * closeCurrentModal
   * @desc closes the current modal and resolves its associated
   *       promise
   * 
   */
  closeCurrentModal() {
    if (isNullOrUndefined(this.modal)) {
      return;
    }

    const { modal, promise, close: closeModal } = this.modal;
    closeModal(promise.cancel);
  }
};


/**
 * Main thread
 * @desc initialises the modal factory once the DOM
 *       is resolved; and adds itself to the global scope
 *       for use within other script(s)
 * 
 */
domReady.finally(() => {
  window.ModalFactory = new ModalFactory();
});
