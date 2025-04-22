import DoubleRangeSlider from '../../components/doubleRangeSlider.js';
import { parseAsFieldType, resolveRangeOpts } from '../entityCreator/utils.js';

/**
 * Class to manage variable & measurement creation
 * 
 * @class
 * @constructor
 */
export default class VariableCreator {
  /**
   * @desc default constructor options
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   */
  static #DefaultOpts = {};

  /**
   * @desc describes the validation params for specific field(s)
   * @type {Record<string, Record<string, any>>}
   * @static
   * @constant
   * 
   */
  static #Validation = {
    name: {
      minlength: 2,
      maxlength: 500,
    },
    description: {
      minlength: 0,
      maxlength: 500,
    },
    string: {
      minlength: 0,
      maxlength: 1024,
    }
  };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = {};

  /**
   * @desc
   * @type {Record<string, Record<string, HTMLElement>>}
   * @private
   */
  #templates = {};

  /**
   * @desc
   * @type {Record<string, any>|null}
   * @private
   */
  #modalState = null;

  /**
   * @param {HTMLElement}         element   the HTMLElement assoc. with this component
   * @param {Record<string, any>} fieldData specifies the initial value, properties, validation, and options of the component
   * @param {Record<string, any>} [opts]    optionally specify any additional component opts; see {@link VariableCreator.#DefaultOpts}
   */
  constructor(element, fieldData, opts) {
    let { value, options, properties, txt } = isObjectType(fieldData) ? fieldData : { };
    txt = isObjectType(txt) ? txt : { };
    options = Array.isArray(options) ? options : [];
    properties = isObjectType(properties) ? properties : { };

    let fieldName = element.getAttribute('data-field');
    fieldName = stringHasChars(fieldName) ? fieldName : 'Variable';
    fieldName = transformTitleCase(fieldName).replace('_', ' ');

    opts = isObjectType(opts) ? opts : {};
    opts.txt = mergeObjects(
      isObjectType(opts.txt)
        ? opts.txt
        : { single: fieldName, plural: fieldName + '(s)' },
      txt
    );
    opts.options = mergeObjects(Array.isArray(opts.options) ? opts.options : [], options, false, true);
    opts.properties = mergeObjects(isObjectType(opts.properties) ? opts.properties : {}, properties, false, true);

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

  /**
   * @desc toggles the page content presentation section 
   * 
   * @return {this}
   */
  #toggleLayoutContentVis(val) {
    const layout = this.#layout;
    if (!layout) {
      return;
    }

    if (val) {
      layout.contentGroup.classList.add('show');
      layout.noneAvailable.classList.remove('show');
      layout?.clearBtn?.classList?.remove?.('hide');
    } else {
      layout.noneAvailable.classList.add('show');
      layout.contentGroup.classList.remove('show');
      layout?.clearBtn?.classList?.add?.('hide');
    }

    return this;
  }

  /**
   * @desc toggles the modal content presentation section 
   * 
   * @return {this}
   */
  #toggleModalContentVis(val) {
    const ctx = this.#modalState?.ctx;
    if (!ctx) {
      return;
    }

    if (val) {
      ctx.content.classList.add('show');
      ctx.none.classList.remove('show');
    } else {
      ctx.none.classList.add('show');
      ctx.content.classList.remove('show');
    }

    return this;
  }


  /*************************************
   *                                   *
   *            Renderables            *
   *                                   *
   *************************************/
  #renderLayout() {
    const layout = this.#layout;
    const templates = this.#templates;
    const { options } = this.props;

    const data = this.data;
    const dataLen = Object.values(data).length;
    clearAllChildren(layout.contentList);

    if (!dataLen) {
      this.#toggleLayoutContentVis(false);
      return this;
    }

    const hasOptions = Array.isArray(options);
    for (const key in data) {
      const item = data[key];
      if (!item) {
        continue;
      }

      let { value, type } = item;

      let processed = false;
      if (hasOptions) {
        let relative = options.find(x => x.name == key);
        relative = !!relative ? relative.value : null;
        if (relative && stringHasChars(relative.format)) {
          value = pyFormat(relative.format, item.value);
          processed = true;
        }
      }

      if (!processed) {
        if (type.endsWith('_range')) {
          const suffix = type.includes('percentage') ? '%' : '';
          value = `${value[0]}${suffix} - ${value[1]}${suffix}`;
        } else if (type.includes('percentage')) {
          value = `${value}%`;
        } else {
          value = value.toString();
        }
      }

      type = transformTitleCase(item.type).replace('_', ' ');
      composeTemplate(templates.vinterface.item, {
        params: {
          ref: key,
          name: `${item.name}`,
          type: `${type}`,
          value: value,
        },
        parent: layout.contentList,
        render: (elem) => {
          elem = elem.shift();

        },
      });
    }
    this.#toggleLayoutContentVis(true);
    return this;
  }

  #openModal(editKey = null) {
    const tmpl = this.props;
    window.ModalFactory.create({
      id: 'var-creator-dialog',
      title: stringHasChars(tmpl?.properties?.label) ? tmpl?.properties?.label : 'Variable Creator',
      size: window.ModalFactory.ModalSizes.Large,
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
      beforeAccept: () => {
        const packet = this.#validatePacket();
        if (!packet || !packet?.success) {
          let message = packet?.message;
          let reqClosure = !stringHasChars(message);
          message = !reqClosure ? message : 'Validation';

          window.ToastFactory.push({
            type: 'danger',
            message: message,
            duration: 3000,
          });

          if (reqClosure) {
            console.error('[VariableCreator::Submit] Failed to submit form.');
            return;
          }

          return new window.ModalFactory.ModalResults('Cancel');
        }

        if (packet.editKey !== this.#modalState.info.editKey) {
          if (this.data?.[this.#modalState.info.editKey]) {
            delete this.data[this.#modalState.info.editKey];
          }
        }
        this.data[packet.editKey] = packet.value;
        return this.data;
      },
      onRender: (modal) => this.#renderOptionPanel(modal, editKey),
    })
      .then(res => {
        this.makeDirty();
        this.#renderLayout();
      })
      .catch(res => {
        this.#modalState = null;

        if (!!res && !(res instanceof ModalFactory.ModalResults)) {
          return console.error(res);
        }
      });
  }

  #renderOptionPanel(modal, editKey = null) {
    const isUpdate = stringHasChars(editKey);

    const ctx = { };
    const state = {
      ctx: ctx,
      data: null,
      isUpdate: isUpdate ? editKey : null,
      isDirty: false,
      isInEditor: false,
    };
    this.#modalState = state;

    const tmpl = this.props;
    const templates = this.#templates;

    const opts = tmpl.options;
    const props = tmpl.properties;

    const hasOpts = Array.isArray(opts) && opts.length > 0;
    const typesAllowed = Array.isArray(props.allow_types) && props.allow_types.length > 0 ? props.allow_types : null;
    const unknownAllowed = !!typesAllowed && !!props.allow_unknown;
    const descriptionAllowed = !!props.allow_description;
    state.hasOpts = hasOpts;
    state.typesAllowed = typesAllowed;
    state.unknownAllowed = unknownAllowed;
    state.descriptionAllowed = descriptionAllowed;

    const innerModal = modal.querySelector('#target-modal-content');
    innerModal.classList.add('slim-scrollbar');

    composeTemplate(templates.vinterface.panel, {
      params: props.selector,
      parent: innerModal,
      render: (elems) => {
        ctx.panel = elems[0];
        ctx.none = ctx.panel.querySelector(':scope > [data-section="none"]');
        ctx.header = ctx.panel.querySelector(':scope > [data-section="header"]');
        ctx.content = ctx.panel.querySelector(':scope > [data-section="content"]');

        if (hasOpts) {
          const selItems = [];
          ctx.selector = ctx.panel.querySelector('#tmpl-selector');

          for (let i = 0; i < opts.length; ++i) {
            selItems.push(createElement('option', {
              value: opts[i].name,
              innerText: opts[i].value.name,
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
            return a.innerText < b.innerText ? -1 : (a.innerText > b.innerText ? 1 : 0);
          });

          for (let i = 0; i < selItems.length; ++i) {
            selItems[i] = ctx.selector.appendChild(selItems[i]);
          }
          ctx.selItems = selItems;
        }

        if (!hasOpts || isUpdate) {
          ctx.header.style.cssText = 'display: none !important; visibility: hidden;';
        }
      }
    });

    if (isUpdate) {
      // Render form with data
      const varopt = hasOpts ? opts.find(x => x.name === editKey) : null;

      const ref = varopt ? editKey : 'unknown';
      const data = deepCopy(this.data[editKey]);
      state.data = data;
      state.info = {
        editKey: editKey,
        ref: ref,
        opts: ref === 'unknown' ? state.typesAllowed : varopt?.value,
        type: data.type,
        label: data.name,
      };
      this.#renderVariableForm();
    } else if (hasOpts) {
      // Render specified
      ctx.selItems.forEach(x => x.hidden = x.value !== 'unknown' && x.value in this.data);

      ctx.selector.addEventListener('change', (e) => {
        const trg = e.target;

        let idx = trg.selectedIndex;
        if (typeof idx !== 'number' || idx < 1) {
          this.#toggleModalContentVis(false);
          return;
        }

        const opt = trg.options[idx];
        const val = opt.value;
        this.#tryOpenEditor(val);
      });
      this.#toggleModalContentVis(false);
    } else {
      // Render custom
      const ref = 'unknown';
      const len = Object.keys(this.data).length + 1;
      const lbl = `Item ${len}`;

      const info = {
        ref: ref,
        opts: state.typesAllowed,
        type: state.typesAllowed[0],
        label: lbl,
        editKey: transformSnakeCase(lbl),
      };

      state.info = info;
      state.data = {
        name: info.label,
        type: info.type,
        value: null,
      };

      this.#renderVariableForm();
    }
  }

  #tryOpenEditor(editKey) {
    const tmpl = this.props;
    const state = this.#modalState;

    let ref, type, opts, label;
    if (editKey === 'unknown') {
      ref = editKey;
      opts = state.typesAllowed;
      type = opts[0];

      const len = Object.keys(this.data).length + 1;
      label = `Item ${len}`
      editKey = transformSnakeCase(label);
    } else {
      opts = tmpl.options.find(x => x.name === editKey);
      opts = opts.value;

      ref = editKey;
      type = opts.type;
      label = opts.name;
    }

    let promise;
    if (!state.isInEditor || !state.isDirty) {
      promise = Promise.resolve();
    } else {
      promise = window.ModalFactory.create({
        id: generateUUID(),
        ref: 'prompt',
        title: 'Are you sure?',
        content: 'You will lose your current progress if you switch to another type without confirming.',
      })
    }

    return promise
      .then(() => {
        let data = this.data[editKey];
        data = isObjectType(data) ? deepCopy(data) : { };

        state.info = { editKey, ref, type, label, opts };
        state.data = {
          name: label,
          type: type,
          value: null,
        };

        this.#renderVariableForm();
      })
      .catch((res) => {
        if (!!res && !(res instanceof ModalFactory.ModalResults)) {
          return console.error(res);
        }
      })
      .finally(() => {
        createElement('a', { href: '#var-creator-dialog' }).click();
      });
  }

  #renderVariableForm() {
    const state = this.#modalState;
    const templates = this.#templates;

    const { ctx, data, info } = state;
    state.isInEditor = true;

    if (!state.isUpdate) {
      state.isDirty = false;
    }

    const disableInputs = state.isUpdate || info.ref !== 'unknown';
    clearAllChildren(ctx.content);

    const ctrls = { };
    state.ctrls = ctrls;

    composeTemplate(templates.inputs.inputbox, {
      params: {
        id: 'name',
        ref: 'name',
        value: data.name,
        label: 'Name',
        placeholder: 'Enter name...',
        disabled: disableInputs ? 'disabled' : '',
        mandatory: true,
        minlength: VariableCreator.#Validation.name.minlength,
        maxlength: VariableCreator.#Validation.name.maxlength,
      },
      parent: ctx.content,
      render: (elem) => {
        elem = elem.shift();
        ctrls.name = elem;

        const input = elem.querySelector('input');
        input.addEventListener('change', (e) => {
          const val = parseAsFieldType({ validation: { type: 'string' } }, e.target.value);
          if (!!val && val?.success) {
            if (val.value !== data.name) {
              state.isDirty = true;
            }

            data.name = val.value;
            e.target.value = val.value;
          }
        });
      },
    });

    if (info.ref === 'unknown') {
      const typeItems = [];
      for (let i = 0; i < state.typesAllowed.length; ++i) {
        const type = state.typesAllowed[i];
        const typeLabel = transformTitleCase(type).replace('_', ' ');
        typeItems.push(createElement('option', { value: type, innerText: typeLabel }));
      }

      typeItems.sort((a, b) => {
        return a.innerText < b.innerText ? -1 : (a.innerText > b.innerText ? 1 : 0);
      });

      const idx = typeItems.findIndex(x => x.value === data.type);
      const dropdown = createElement('select', {
        childNodes: typeItems,
        attributes: {
          id: 'type',
          name: 'type',
        },
        selectedIndex: idx,
      });
      dropdown.setAttribute('placeholder-text', 'Select Type...');

      ctrls.dropdown = {
        group: createElement('div', {
          parent: ctx.content,
          className: 'input-field-container number-input',
          dataset: {
            ref: 'type',
            ctrl: 'dropdown',
          },
          childNodes: [
            `<p class="input-field-container__label input-field-container--fill-w">
              Datatype
              <span class="input-field-container__mandatory">*</span>
            </p>`,
            dropdown
          ],
        }),
        element: dropdown,
      };

      if (disableInputs) {
        dropdown.disabled = true;
      } else {
        dropdown.addEventListener('change', (e) => {
          const trg = dropdown.options?.[dropdown.selectedIndex];
          if (isHtmlObject(ctrls.value)) {
            ctrls.value.remove();
          } else if (ctrls?.value?.getElement) {
            ctrls.value.getElement().remove();
          }
  
          data.type = trg.value;
          data.value = null;
  
          this.#renderValueFieldComponent(state.descriptionAllowed ? ctrls.description : null);
        });
      }
    }
    this.#renderValueFieldComponent();

    if (state.descriptionAllowed) {
      composeTemplate(templates.inputs.inputbox, {
        params: {
          id: 'description',
          ref: 'description',
          value: !isNullOrUndefined(data.description) ? data.description : '',
          label: 'Description',
          placeholder: 'Enter description...',
          disabled: '',
          mandatory: false,
          minlength: VariableCreator.#Validation.description.minlength,
          maxlength: VariableCreator.#Validation.description.maxlength,
        },
        parent: ctx.content,
        render: (elem) => {
          elem = elem.shift();
          ctrls.description = elem;

          const input = elem.querySelector('input');
          input.addEventListener('change', (e) => {
            const val = parseAsFieldType({ validation: { type: 'string' } }, e.target.value);
            if (!!val && val?.success) {
              if (val.value !== data.description) {
                state.isDirty = true;
              }

              data.description = val.value;
              e.target.value = val.value;
            }
          });
        },
      });
    }

    this.#toggleModalContentVis(true);
  }

  #renderValueFieldComponent(parent = null) {
    const state = this.#modalState;
    const templates = this.#templates;

    const { ctx, data, info, ctrls } = state;
    switch (data.type) {
      case 'int':
      case 'float':
      case 'decimal':
      case 'numeric':
      case 'percentage': {
        const range = resolveRangeOpts(data.type, info.opts);
        data.value = !isNullOrUndefined(data.value) ? data.value : 0;

        composeTemplate(templates.inputs.number, {
          params: {
            id: 'value',
            ref: 'value',
            type: data.type,
            step: range.attr.step,
            label: 'Value',
            btnStep: range.values.step,
            rangemin: range.attr.min,
            rangemax: range.attr.max,
            value: !isNullOrUndefined(data.value) ? data.value : '',
            placeholder: 'Number value...',
            disabled: '',
            mandatory: true,
          },
          render: (elem) => {
            elem = elem.shift();
            if (!isHtmlObject(parent)) {
              elem = ctx.content.appendChild(elem);
            } else {
              elem = ctx.content.insertBefore(elem, parent);
            }
            ctrls.value = elem;

            const fieldValidation = { validation: { type: data.type } };
            if (!isNullOrUndefined(range.values.min) && !isNullOrUndefined(range.values.max)) {
              fieldValidation.validation.range = [fmin, fmax];
            }

            const input = elem.querySelector('input');
            input.value = data.value;

            input.addEventListener('change', (e) => {
              const val = parseAsFieldType(fieldValidation, input.value);
              if (!!val && val?.success) {
                if (val.value !== data.value) {
                  state.isDirty = true;
                }
                data.value = val.value;
                input.value = val.value;
              }
            });
          },
        });
      } break;

      case 'string': {
        data.value = !isNullOrUndefined(data.value) ? data.value : '';

        composeTemplate(templates.inputs.inputbox, {
          params: {
            id: 'value',
            ref: 'value',
            value: !isNullOrUndefined(data.value) ? data.value : '',
            label: 'Value',
            placeholder: 'String value...',
            disabled: '',
            mandatory: true,
            minlength: VariableCreator.#Validation.string.minlength,
            maxlength: VariableCreator.#Validation.string.maxlength,
          },
          render: (elem) => {
            elem = elem.shift();
            if (!isHtmlObject(parent)) {
              elem = ctx.content.appendChild(elem);
            } else {
              elem = ctx.content.insertBefore(elem, parent);
            }
            ctrls.value = elem;

            elem.querySelector('input').addEventListener('change', (e) => {
              const val = parseAsFieldType({ validation: { type: 'string' } }, e.target.value);
              if (!!val && val?.success) {
                if (val.value !== data.value) {
                  state.isDirty = true;
                }

                data.value = val.value;
                e.target.value = val.value;
              }
            });
          },
        });
      } break;

      case 'ci_interval': {
        if (!isObjectType(data.value)) {
          data.value = {
            probability: 95,
            lower: 0,
            upper: 0,
          };
        }

        composeTemplate(templates.inputs.ciinterval, {
          params: {
            id: 'value',
            ref: 'value',
            label: 'Value',
            upper: data.value.upper,
            lower: data.value.lower,
            probability: data.value.probability,
            disabled: '',
            mandatory: true,
          },
          render: (elem) => {
            elem = elem.shift();
            if (!isHtmlObject(parent)) {
              elem = ctx.content.appendChild(elem);
            } else {
              elem = ctx.content.insertBefore(elem, parent);
            }
            ctrls.value = elem;

            const lowerElem = elem.querySelector('input[name="lower"]');
            const upperElem = elem.querySelector('input[name="upper"]');
            const probabilityElem = elem.querySelector('input[name="probability"]');

            const onChange = (e) => {
              const trg = e.target.getAttribute('name');

              let val = { ...data.value };
              val[trg] = e.target.value ?? 0;

              val = parseAsFieldType({ validation: { type: data.type } }, val);
              if (!!val && val?.success) {
                const { lower, upper, probability } = val.value;
                data.value.lower = Math.min(lower, upper);
                data.value.upper = Math.max(lower, upper);
                data.value.probability = probability;

                lowerElem.value = data.value.lower;
                upperElem.value = data.value.upper;
                probabilityElem.value = data.value.probability;

                state.isDirty = true;
              }
            };

            lowerElem.addEventListener('change', onChange);
            upperElem.addEventListener('change', onChange);
            probabilityElem.addEventListener('change', onChange);
          },
        });
      } break;

      case 'int_range':
      case 'float_range':
      case 'decimal_range':
      case 'numeric_range':
      case 'percentage_range': {
        const type = data.type.split('_').shift();
        const range = resolveRangeOpts(data.type, info.opts);

        const {
          min: fmin,
          max: fmax,
          step: fstep
        } = range.values;

        const hasRangeValues = (
          typeof fmin === 'number' &&
          typeof fmax === 'number' &&
          typeof fstep === 'number'
        );

        if (!Array.isArray(data.value)) {
          let vmax = type === 'int' ? 100 : 1;
          vmax = isNullOrUndefined(fmin) ? vmax : fmin + vmax;

          data.value = [
            isNullOrUndefined(fmin) ? fmin : 0,
            isNullOrUndefined(fmax) ? fmax : vmax,
          ];
        }

        if (hasRangeValues) {
          composeTemplate(templates.inputs.rangeslider, {
            params: {
              id: 'value',
              ref: 'value',
              type: type,
              label: 'Value',
              disabled: '',
              mandatory: true,
            },
            render: (elem) => {
              elem = elem.shift();
              if (!isHtmlObject(parent)) {
                elem = ctx.content.appendChild(elem);
              } else {
                elem = ctx.content.insertBefore(elem, parent);
              }

              ctrls.value = new DoubleRangeSlider(elem, {
                value: {
                  min: data.value[0],
                  max: data.value[1],
                },
                properties: {
                  min: fmin,
                  max: fmax,
                  step: fstep,
                  type: 'float',
                },
              });

              elem.addEventListener('change', (e) => {
                let val = ctrls.value.getValue();
                val = parseAsFieldType({ validation: { type: data.type, range: [fmin, fmax] } }, [val.min, val.max]);
                if (!!val && val?.success) {
                  data.value = val.value;
                  state.isDirty = true;
                }
              });
            },
          });
        } else {
          const minValue = typeof data.value[0] === 'number' ? `${data.value[0]}` : '0';
          const maxValue = typeof data.value[1] === 'number' ? `${data.value[1]}` : '0';
          composeTemplate(templates.inputs.numericrange, {
            params: {
              id: 'value',
              ref: 'value',
              label: 'Value',
              type: type,
              min: minValue,
              max: maxValue,
              step: range.attr.step,
              btnStep: range.values.step,
              disabled: '',
              mandatory: true,
            },
            render: (elem) => {
              elem = elem.shift();
              if (!isHtmlObject(parent)) {
                elem = ctx.content.appendChild(elem);
              } else {
                elem = ctx.content.insertBefore(elem, parent);
              }
              ctrls.value = elem;
  
              const minElem = elem.querySelector('input[name="min"]');
              const maxElem = elem.querySelector('input[name="max"]');
  
              const onChange = (e) => {
                const trg = e.target.getAttribute('name');
                const val = parseAsFieldType({ validation: { type: type } }, e.target.value);
                if (!!val && val?.success) {
                  data.value[trg === 'min' ? 0 : 1] = val.value;
                  data.value.sort();
                  state.isDirty = true;
  
                  minElem.value = data.value[0];
                  maxElem.value = data.value[1];
                }
              };
  
              minElem.addEventListener('change', onChange);
              maxElem.addEventListener('change', onChange);
            },
          });
        }
      } break;

      default:
        break;
    }
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #initEvents() {
    const data = this.data;
    const layout = this.#layout;
    const element = this.element;
    const fieldText = this.props.txt;

    document.addEventListener('click', (e) => {
      const target = e.target;
      if (!element.contains(target) || !target.matches('[data-fn="button"][data-owner="var-selector"]')) {
        return true;
      }

      const action = target.getAttribute('data-action');
      if (!stringHasChars(action)) {
        return true;
      }

      const ref = target.getAttribute('data-ref');
      e.preventDefault();

      if (stringHasChars(ref) && layout.contentList.contains(target)) {
        // Item action button(s)
        const item = this.data[ref];
        if (!item) {
          return true;
        }

        switch (action) {
          case 'edit': {
            this.#openModal(ref);
          } break;
  
          case 'remove': {
            window.ModalFactory.create({
              id: generateUUID(),
              ref: 'prompt',
              title: 'Are you sure?',
              content: `Are you sure you want to delete the ${fieldText.single} "${item.name}"? This action cannot be reverted.`,
            })
              .then(_ => {
                if (this.data?.[ref]) {
                  delete this.data[ref];
                }

                const elem = tryGetRootElement(target, '[data-area="item"]');
                if (!elem) {
                  this.#renderLayout();
                  return;
                }

                const len = Object.keys(data).length;
                elem.remove();

                this.#toggleLayoutContentVis(len > 0);
              })
              .catch(res => {
                if (!!res && !(res instanceof ModalFactory.ModalResults)) {
                  return console.error(res);
                }
              });
          } break;
  
          default:
            break;
        }

        return false;
      }

      // Action bar button(s)
      switch (action) {
        case 'add':
          this.#openModal();
          break;

        case 'clear': {
          const len = Object.keys(data).length;
          if (len < 1) {
            break;
          }

          window.ModalFactory.create({
            id: generateUUID(),
            ref: 'prompt',
            title: 'Are you sure?',
            content: `Are you sure you want to delete all ${len}x ${fieldText.plural}? Please note that this action cannot be undone without losing all other page progress.`,
          })
            .then(_ => {
              for (const key in data) {
                if (!data.hasOwnProperty(key)) {
                  continue;
                }

                delete data[key];
              }

              this.#renderLayout();
            })
            .catch(res => {
              if (!!res && !(res instanceof ModalFactory.ModalResults)) {
                return console.error(res);
              }
            });
        } break;

        default:
          break;
      }

      return false;
    });
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  #validatePacket() {
    const modalState = this.#modalState;
    const validation = VariableCreator.#Validation;
    if (!modalState) {
      return false;
    }

    let { info, data, typesAllowed, unknownAllowed } = modalState;
    if (!info || !data) {
      return false;
    }

    let fval = validation.name;
    let name = parseAsFieldType(
      {
        validation: {
          type: 'string',
          regex: '[^\s]+',
          properties: {
            validateLen: true,
            length: [fval.minlength, fval.maxlength],
          },
        },
      },
      strictSanitiseString(data.name),
    );

    if (!name || !name?.success) {
      if (isObjectType(name?.value) && name.value?.len) {
        let msg;
        if (fval.minlength > 0) {
          msg = `must be at least ${fval.minlength} characters long, with a maximum length of ${fval.maxlength} characters.`;
        } else {
          msg = `cannot have more than ${fval.maxlength} characters.`;
        }

        return {
          success: false,
          message: `Name ${msg}`,
        };
      }

      return {
        success: false,
        message: 'Name is a required string field.',
      };
    } else {
      name = name.value;
    }

    let description = data.description;
    fval = validation.description;

    if (typeof description === 'string') {
      description = parseAsFieldType(
        {
          validation: {
            type: 'string',
            regex: '[^\s]+',
            properties: {
              validateLen: true,
              length: [fval.minlength, fval.maxlength],
            },
          },
        },
        strictSanitiseString(description),
      );

      if (!description || !description?.success) {
        if (isObjectType(description?.value) && description.value?.len) {
          let msg;
          if (fval.minlength > 0) {
            msg = `must be at least ${fval.minlength} characters long, with a maximum length of ${fval.maxlength} characters.`;
          } else {
            msg = `cannot have more than ${fval.maxlength} characters.`;
          }

          return {
            success: false,
            message: `If provided, the description ${msg}`,
          };
        }
        description = null;
      } else {
        description = description.value;
      }
    } else {
      description = null;
    }

    let type, value;
    type = data.type;

    let invalid = false;
    const relative = this.props.options.find(x => x.name === info.editKey);
    if (info.ref === 'unknown') {
      invalid = !unknownAllowed || typeof type !== 'string' || !typesAllowed.includes(type);
    } else {
      invalid = typeof type !== 'string' || !relative || relative?.value?.type !== type;
    }

    if (invalid) {
      return false;
    }

    fval = validation?.[type];
    value = data.value;

    if (type === 'string') {
      value = strictSanitiseString(value);
      value = parseAsFieldType(
        {
          validation: {
            type: 'string',
            regex: '[^\s]+',
            properties: {
              validateLen: true,
              length: [fval.minlength, fval.maxlength],
            },
          },
        },
        value,
      );

      if (!value || !value?.success) {
        if (isObjectType(value?.value) && value.value?.len) {
          let msg;
          if (fval.minlength > 0) {
            msg = `must be at least ${fval.minlength} characters long, with a maximum length of ${fval.maxlength} characters.`;
          } else {
            msg = `cannot have more than ${fval.maxlength} characters.`;
          }

          return {
            success: false,
            message: `The value ${msg}`,
          };
        }

        return {
          success: false,
          message: 'The value field must not be empty.',
        };
      } else {
        value = value.value;
      }
    }

    return {
      success: true,
      editKey: relative ? info.editKey : transformSnakeCase(name),
      isRelative: !!relative,
      value: { name, type, value, description },
    };
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise() {
    const elem = this.element;
    const layout = this.#layout;
    elem.querySelectorAll('[data-area]').forEach(v => {
      const role = v.getAttribute('data-area');
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

    this.#initEvents();
    this.#renderLayout();
  }
};
