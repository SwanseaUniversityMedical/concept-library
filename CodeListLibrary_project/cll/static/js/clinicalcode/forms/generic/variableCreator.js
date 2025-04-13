export default class VariableCreator {
  /**
   * @desc default constructor options
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   */
  static #DefaultOpts = {

  };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = {};

  /**
   * @desc
   * @type {Record<string, Record<string, HTMLElement>}
   * @private
   */
  #templates = {};

  /**
   * @param {HTMLElement}         element   the HTMLElement assoc. with this component
   * @param {Record<string, any>} fieldData specifies the initial value, properties, validation, and options of the component
   * @param {Record<string, any>} [opts]    optionally specify any additional component opts; see {@link VariableCreator.#DefaultOpts}
   */
  constructor(element, fieldData, opts) {
    let { value, options, properties } = fieldData;
    opts = isObjectType(opts) ? opts : {};
    opts.options = mergeObjects(isObjectType(opts.options) ? opts.options : {}, options, false, true)
    opts.properties = mergeObjects(isObjectType(opts.properties) ? opts.properties : {}, properties, false, true)

    this.data = isObjectType(value) ? value : {};
    this.props = mergeObjects(opts, VariableCreator.#DefaultOpts);
    this.dirty = false;
    this.element = element;

    this.#initialise();
  }


  /*************************************
   *                                   *
   *              Getter               *
   *                                   *
   *************************************/
  /**
   * @returns {Record<string, any>} an obj describing the variables contained by this component
   */
  getData() {
    return this.data;
  }

  /**
   * @returns {HTMLElement} the assoc. element
   */
  getElement() {
    return this.element;
  }

  /**
   * @returns {bool} returns the dirty state of this component
   */
  isDirty() {
    return this.dirty;
  }


  /*************************************
   *                                   *
   *              Setter               *
   *                                   *
   *************************************/
  /**
   * @desc informs the top-level parent that we're dirty and updates our internal dirty state
   * 
   * @return {this}
   */
  makeDirty() {
    window.entityForm.makeDirty();
    this.dirty = true;
    return this;
  }


  /*************************************
   *                                   *
   *            Renderables            *
   *                                   *
   *************************************/
  #renderOptionPanel(modal, types) {
    const ctx = { };
    const state = { };

    const tmpl = this.props;
    const layout = this.#layout;
    const templates = this.#templates;

    const opts = tmpl.options;
    const props = tmpl.properties;

    const hasOpts = isObjectType(opts) && Object.keys(opts).length > 0;
    const typesAllowed = Array.isArray(props.allow_types) ? props.allow_types : null;
    const unknownAllowed = !!typesAllowed && !!props.allow_unknown;
    const descriptionAllowed = !!props.allow_description;
    state.hasOpts = hasOpts;
    state.typesAllowed = typesAllowed;
    state.unknownAllowed = unknownAllowed;
    state.descriptionAllowed = state.descriptionAllowed;

    const innerModal = modal.querySelector('#target-modal-content');
    composeTemplate(templates.vinterface.panel, {
      params: {
        title: 'Select Measure',
        label: 'Options...',
      },
      parent: innerModal,
      render: (elems) => {
        ctx.panel = elems[0];
        ctx.content = ctx.panel.querySelector(':scope > [data-role="content"]');

        if (hasOpts) {
          const selItems = [];
          ctx.selector = ctx.panel.querySelector('#tmpl-selector');

          for (const key in opts) {
            selItems.push(createElement('option', {
              value: opts[key].name,
              innerText: opts[key].value.name,
            }));
          }
  
          if (unknownAllowed) {
            selItems.push(createElement('option', {
              value: 'unknown',
              innerText: 'Custom Measure',
              parent: ctx.selector,
            }));
          }
  
          selItems.sort((a, b) => {
            return a.innerText < b.innerText;
          });
  
          for (let i = 0; i < selItems.length; ++i) {
            selItems[i] = ctx.selector.append(selItems[i]);
          }
          state.selItems = selItems;
        }

        if (unknownAllowed) {
          const typeItems = [];
        }
      }
    });

    composeTemplate(templates.inputs.number, {
      params: {
        id: 'num',
        ref: 'num',
        type: 'percentage',
        step: 'step="0.01"',
        label: 'Value',
        btnStep: '', // step="1" | step="0.01" etc
        rangemin: '', // min="0"
        rangemax: '', // max="0"
        value: 0,
        placeholder: 'Number value...',
      },
      parent: ctx.content,
    });

    composeTemplate(templates.inputs.inputbox, {
      params: {
        id: 'str',
        ref: 'str',
        value: '',
        label: 'Description',
        placeholder: 'Enter text...',
      },
      parent: ctx.content,
    });
  }

  #openModal() {
    const tmpl = this.props;
    window.ModalFactory.create({
      title: 'Modal',
      size: window.ModalFactory.ModalSizes.XLarge,
      content: '',
      buttons: [
        {
          name: 'Confirm',
          type: window.ModalFactory.ButtonTypes.CONFIRM,
          html: `<button class="primary-btn text-accent-darkest bold secondary-accent" id="confirm-button"></button>`,
        },
        {
          name: 'Cancel',
          type: window.ModalFactory.ButtonTypes.REJECT,
          html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="reject-button"></button>`,
        },
      ],
      beforeAccept: (modal) => {

      },
      onRender: (modal) => {
        const opts = tmpl.options;
        this.#renderOptionPanel(modal);
      }
    })
      .then(res => {
        console.log(res);
      })
      .catch(res => {
        console.warn(res);
      });
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/



  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/



  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise() {
    const elem = this.element;
    const layout = this.#layout;
    elem.querySelectorAll('[data-role]').forEach(v => {
      const role = v.getAttribute('data-role');
      if (stringHasChars(role)) {
        layout[role] = v;
      }
    });

    const templates = this.#templates;
    elem.querySelectorAll('template[data-name]').forEach(v => {
      let name = v.getAttribute('data-name');
      let view = v.getAttribute('data-view');
      if (!stringHasChars(view)) {
        view = 'base';
      }

      let group =  templates?.[view];
      if (!group) {
        group = { };
        templates[view] = group;
      }

      group[name] = v;
    });

    this.#setUp();
  }

  #setUp() {
    const layout = this.#layout;
    layout.addBtn.addEventListener('click', (e) => {
      this.#openModal();
    });
  }
};
