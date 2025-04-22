export default class IndicatorCalculationCreator {
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
   * @desc default field placeholder / values to compare against
   * @type {string}
   * @static
   * @constant
   * 
   */
  static #DefaultValues = {
    description: `#### Type of Measurement\n\n\n\n#### Description\n\n`,
    numerator: `#### Description\n\n\n\n#### Inclusions\n\n- ...\n\n#### Exclusions\n\n- ...\n`,
    denominator: `#### Description\n\n\n\n#### Inclusions\n\n- ...\n\n#### Exclusions\n\n- ...\n`,
  };

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  #layout = {};

  /**
   * @desc
   * @type {Record<string, HTMLElement>}
   * @private
   */
  elements = {};

  /**
   * @param {HTMLElement}         element   the HTMLElement assoc. with this component
   * @param {Record<string, any>} fieldData specifies the initial value, properties, validation, and options of the component
   * @param {Record<string, any>} [opts]    optionally specify any additional component opts; see {@link VariableCreator.#DefaultOpts}
   */
  constructor(element, fieldData, opts) {
    this.data = isObjectType(fieldData) ? fieldData : { description: '', numerator: '', denominator: '' };
    this.dirty = false;
    this.element = element;

    this.#initialise();
  }

  /*************************************
   *                                   *
   *              Getter               *
   *                                   *
   *************************************/
  static IsDefaultValue(role, value) {
    if (!stringHasChars(value)) {
      return true;
    }

    const comp = IndicatorCalculationCreator.#DefaultValues?.[role];
    if (!stringHasChars(comp)) {
      return false;
    }

    return comp.trim() === value.trim();
  }

  /*************************************
   *                                   *
   *              Getter               *
   *                                   *
   *************************************/
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
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise() {
    const elem = this.element;
    const layout = this.#layout;
    const elements = this.elements;
    elem.querySelectorAll('[data-role]').forEach(v => {
      const role = v.getAttribute('data-role');
      if (!stringHasChars(role)) {
        return;
      }

      const mde = new EasyMDE({
        // Elem
        element: v,
        maxHeight: '300px',
        minHeight: '200px',
  
        // Behaviour
        autofocus: false,
        forceSync: false,
        autosave: { enabled: false },
        placeholder: 'Enter content here...',
        promptURLs: false,
        spellChecker: false,
        lineWrapping: true,
        unorderedListStyle: '-',
        renderingConfig: {
          singleLineBreaks: false,
          codeSyntaxHighlighting: false,
          sanitizerFunction: (renderedHTML) => strictSanitiseString(renderedHTML, { html: true }),
        },
  
        // Controls
        status: ['lines', 'words', 'cursor'],
        tabSize: 2,
        toolbar: [
          'heading', 'bold', 'italic', 'strikethrough', '|',
          'unordered-list', 'ordered-list', 'code', 'quote', '|',
          'link', 'image', 'table', '|',
          'preview', 'guide',
        ],
        toolbarTips: true,
        toolbarButtonClassPrefix: 'mde',
      });
      
      let curContent = this.data?.[role];
      curContent = !stringHasChars(curContent) ? IndicatorCalculationCreator.#DefaultValues?.[role] : curContent;

      if (stringHasChars(curContent)) {
        mde.value(curContent);
      }

      layout[role] = v;
      elements[role] = mde;
    });
  }
};
