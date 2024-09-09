/**
 * CSEL_VIEWS
 * @desc describes the view states of this component
 */
const CSEL_VIEWS = {
    // The search view whereby users can select Concepts
    ATTRIBUTE_TABLE: 0,
  
    // The current selection view, only accessible when allowMultiple flag is set to true
    SELECTION: 1,
  };
  
  /**
   * CSEL_EVENTS
   * @desc used internally to track final state of dialogue
   */
  const CSEL_EVENTS = {
    // When a dialogue is cancelled without changes
    CANCELLED: 0,
  
    // When a dialogue is confirmed, with or without changes
    CONFIRMED: 1,
  };
  
  /**
   * CSEL_OPTIONS
   * @desc Available options for this component,
   *       where each of the following options are used as default values
   *       and are appended automatically if not overriden.
   */
  const CSEL_OPTIONS = {
    // Which template to query when retrieving accessible entities
    template: 1,
  
    // Related entity ids to filter the entity from results
    entity_id: null,
    entity_history_id: null,
    concept_data: null,
  
    // Allow more than a single Concept to be selected
    allowMultiple: true,
  
    // Whether to remember the selection when previously opened
    //  [!] Note: Only works when allowMultiple flag is set to true
    maintainSelection: true,
  
    // Flag to determine whether we scroll to the top of the result page when pagination occurs
    scrollOnResultChange: true,
  
    // The title of the prompt
    promptTitle: 'Import Concepts',
  
    // The confirm button text
    promptConfirm: 'Confirm',
  
    // The cancel button text
    promptCancel: 'Cancel',
  
    // The size of the prompt (ModalFactory.ModalSizes.%s, i.e., {sm, md, lg})
    promptSize: 'lg',
  
    // The message shown when no items are selected
    noneSelectedMessage: 'You haven\'t selected any attributes yet',
  
    // Whether to maintain applied filters when user enters/exits the search dialogue
    maintainFilters: true,
  
    // Filters to ignore (by field name)
    ignoreFilters: [ ],
  
    // Force context of filters
    forceFilters: { },
  
    // Which filters, if any, to apply to children
    childFilters: ['coding_system'],
  
    // Whether to cache the resulting queries for quicker,
    // albeit possibly out of date, Phenotypes and their assoc. Concepts
    useCachedResults: false,
  };
  
  /**
   * CSEL_BUTTONS
   * @desc The styleguide for the prompt's buttons
   */
  const CSEL_BUTTONS = {
    CONFIRM: '<button class="primary-btn text-accent-darkest bold secondary-accent" aria-label="Confirm" id="confirm-button"></button>',
    CANCEL: '<button class="secondary-btn text-accent-darkest bold washed-accent" aria-label="Cancel" id="reject-button"></button>',
  };
  
  /**
   * CSEL_INTERFACE
   * @desc defines the HTML used to render the selection interface
   */
  const CSEL_INTERFACE = {
    // Main dialogue modal
    DIALOGUE: ' \
    <div class="target-modal target-modal-${promptSize}" id="${id}" aria-hidden="${hidden}"> \
      <div class="target-modal__container"> \
        <div class="target-modal__header"> \
          <h2 id="target-modal-title">${promptTitle}</h2> \
        </div> \
        <div class="target-modal__body" id="target-modal-content"> \
        </div> \
      </div> \
    </div> \
    <div id="wrapper">\
    </div>',
  
    // Tabbed views when allowMultiple flag is active
    TAB_VIEW: ' \
    <div class="tab-view" id="tab-view"> \
      <div class="tab-view__tabs tab-view__tabs-z-buffer"> \
        <button aria-label="tab" id="ATTRIBUTE_TABLE" class="tab-view__tab active">Attributed Concepts</button> \
        <button aria-label="tab" id="SELECTION" class="tab-view__tab">All attributes</button> \
      </div> \
      <div class="tab-view__content" id="tab-content"> \
      </div> \
    </div>',
  
    SELECTION_VIEW: ' \
    <div class="detailed-input-group fill no-margin"> \
      <div class="detailed-input-group__header"> \
      </div> \
      <section class="detailed-input-group__none-available" id="no-items-selected"> \
        <p class="detailed-input-group__none-available-message">${noneSelectedMessage}</p> \
      </section> \
      <fieldset class="code-search-group indented scrollable slim-scrollbar" id="item-list"> \
      </fieldset> \
    </div>',

  
  
    // Card chip tags group
    CHIP_GROUP: ' \
    <div class="entity-card__snippet-tags"> \
      <div class="entity-card__snippet-tags-group" id="chip-tags"> \
        ${tags} \
      </div> \
    </div>',
  
    // Card chip for result card
    CHIP_TAGS: ' \
    <div class="meta-chip meta-chip-washed-accent"> \
      <span class="meta-chip__name meta-chip__name-text-accent-dark meta-chip__name-bold">${name}</span> \
    </div>',
  
    // Card accordian for children data
    CARD_ACCORDIAN: ' \
    <div class="fill-accordian" id="children-accordian-${id}" style="margin-top: 0.5rem"> \
      <input class="fill-accordian__input" id="children-${id}" name="children-${id}" type="checkbox" /> \
      <label class="fill-accordian__label" id="children-${id}" for="children-${id}" role="button" tabindex="0"> \
        <span>${title}</span> \
      </label> \
      <article class="fill-accordian__container" id="data" style="padding: 0.5rem;"> \
        ${content} \
      </article> \
    </div>',
  
    // Child selector for cards
    CHILD_SELECTOR: ' \
    <div class="checkbox-item-container ${!isSelector? "ignore-overflow" : ""}" id="${isSelector ? "child-selector" : "selected-item" }"> \
      <input id="${field}-${id}" aria-label="${title}" type="checkbox" ${checked ? "checked" : ""} data-index="${index}" \
        class="checkbox-item" data-id="${id}" data-history="${history_id}" \
        data-name="${title}" data-field="${field}" data-prefix="${prefix}" data-coding="${coding_system}"/> \
      <label for="${field}-${id}" class="constrained-filter-item">${title} [${coding_system}]</label> \
    </div>',
  };
  
  

  
  /**
   * @class ConceptSelectionService
   * @desc Class that can be used to prompt users to select 1 or more concepts
   *       from a list given by the server, where:
   *          
   *          1. The owner phenotype is published
   *            OR
   *          2. The requesting user has access to the child concepts via permissions
   * 
   */
  export class AttributeSelectionService {
    static Views = CSEL_VIEWS;
    
  
    constructor(options, data) {
      this.id = generateUUID();
      this.options = mergeObjects(options || { }, CSEL_OPTIONS);
      this.query = { }
  
      if (this.options.allowMultiple) {
        this.data = data || [ ];
      } else {
        this.data = [ ];
      }
    }

   
  
  
    /*************************************
     *                                   *
     *               Getter              *
     *                                   *
     *************************************/
    /**
     * getID
     * @desc gets the ID associated with this instance
     * @returns {string} the assoc. UUID
     */
    getID() {
      return this.id;
    }
  
    /**
     * getQuery
     * @desc gets the current search query params
     * @returns {object} the current query
     */
    getQuery() {
      return this.query;
    }
  
    /**
     * getSelection
     * @desc gets the currently selected concepts
     * @returns {array} the assoc. data
     */
    getSelection() {
      return this.data;
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
  
    /**
     * isSelected
     * @param {number} childId 
     * @param {number} childVersion 
     * @returns {boolean} that reflects the selected state of a Concept
     */
    isSelected(childId, childVersion) {
      if (isNullOrUndefined(this.dialogue?.data)) {
        return false;
      }
  
      return !!this.dialogue.data.find(item => {
        return item.id == childId && item.history_id == childVersion;
      });
    }
  
  
    /*************************************
     *                                   *
     *               Setter              *
     *                                   *
     *************************************/  
    /**
     * setSelection
     * @desc sets the currently selected concepts
     * @param {array} data the desired selected objects
     */
    setSelection(data) {
      data = data || [ ];
  
      if (this.options.allowMultiple) {
        this.data = data;
      }
      return this;
    }
  
  
    /*************************************
     *                                   *
     *               Public              *
     *                                   *
     *************************************/
    /**
     * show
     * @desc shows the dialogue
     * @param {enum|int} view the view to open the modal with 
     * @param {object|null} params query parameters to be provided to server to modify Concept results 
     * @returns {promise} a promise that resolves if the selection was confirmed, otherwise rejects
     */
    show(view = CSEL_VIEWS.ATTRIBUTE_TABLE, params) {
      params = params || { };
  
      // Reject immediately if we currently have a dialogue open
      if (this.dialogue) {
        return Promise.reject();
      }
  
      return new Promise((resolve, reject) => {
          this.#buildDialogue(params);
          this.#renderView(view);
          this.#createGridTable(this.options.concept_data)

          this.dialogue.element.addEventListener('selectionUpdate', (e) => {
            this.close();
    
            const detail = e.detail;
            const eventType = detail.type;
            const data = detail.data;
            switch (eventType) {
              case CSEL_EVENTS.CONFIRMED: {
                if (this.options.allowMultiple && this.options.maintainSelection) {
                  this.data = data;
                }
    
                if (this.options.allowMultiple) {
                  resolve(data);
                  return;
                }
                resolve(data?.[0]);
              } break;
    
              case CSEL_EVENTS.CANCELLED: {
                reject();
              } break;
    
              default: break;
            }
          });
          
          this.dialogue.show();
        })
    }
    
    /**
     * close
     * @desc closes the dialogue if active
     */
    close() {
      if (this.dialogue) {
        this.dialogue.close();
      }
  
      return this;
    }
  
  
  
    /*************************************
     *                                   *
     *               Render              *
     *                                   *
     *************************************/
    /**
     * buildDialogue
     * @desc renders the top-level modal according to the options given
     * @param {object} params the given query params
     * @returns {object} the dialogue object as assigned to this.dialogue
     */
    #buildDialogue(params) {
      // create dialogue
      const currentHeight = window.scrollY;
      let html = interpolateString(CSEL_INTERFACE.DIALOGUE, {
        id: this.id,
        promptTitle: this.options?.promptTitle,
        promptSize: this.options?.promptSize,
        hidden: 'false',
      });
    
      let doc = parseHTMLFromString(html);
      let modal = document.body.appendChild(doc.body.children[0]);
      
      // create footer
      let footer = createElement('div', {
        id: 'target-modal-footer',
        class: 'target-modal__footer',
      });
    
      const container = modal.querySelector('.target-modal__container');
      footer = container.appendChild(footer);
      
      // create buttons
      const buttons = { };
      let confirmBtn = parseHTMLFromString(CSEL_BUTTONS.CONFIRM);
      confirmBtn = footer.appendChild(confirmBtn.body.children[0]);
      confirmBtn.innerText = this.options.promptConfirm;
  
      let cancelBtn = parseHTMLFromString(CSEL_BUTTONS.CANCEL);
      cancelBtn = footer.appendChild(cancelBtn.body.children[0]);
      cancelBtn.innerText = this.options.promptCancel;
  
      buttons['confirm'] = confirmBtn;
      buttons['cancel'] = cancelBtn;
  
      // initiate main event handling
      buttons?.confirm.addEventListener('click', this.#handleConfirm.bind(this));
      buttons?.cancel.addEventListener('click', this.#handleCancel.bind(this));
  
      // create content handler
      const body = container.querySelector('#target-modal-content');
      if (this.options?.allowMultiple) {
        body.classList.add('target-modal__body--no-pad');
        body.classList.add('target-modal__body--constrained');
      }
  
      let contentContainer = body;
      if (this.options.allowMultiple) {
        html = CSEL_INTERFACE.TAB_VIEW;
        doc = parseHTMLFromString(html);
        contentContainer = body.appendChild(doc.body.children[0]);
        
        const tabs = contentContainer.querySelectorAll('button.tab-view__tab');
        for (let i = 0; i < tabs.length; ++i) {
          tabs[i].addEventListener('click', this.#changeTabView.bind(this));
        }
  
        contentContainer = contentContainer.querySelector('#tab-content');
      }
  
      // build dialogue
      this.dialogue = {
        // data
        data: this.options?.maintainSelection ? this.data : [],
        params: params,
        view: CSEL_VIEWS.ATTRIBUTE_TABLE,
  
        // dialogue elements
        element: modal,
        buttons: buttons,
        content: contentContainer,
  
        // dialogue methods
        show: () => {
          createElement('a', { href: `#${this.id}` }).click();
          window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
      
          // inform screen readers of alert
          modal.setAttribute('aria-hidden', false);
          modal.setAttribute('role', 'alert');
          modal.setAttribute('aria-live', true);
          
          // stop body scroll
          document.body.classList.add('modal-open');
        },
        close: () => {
          this.dialogue = null;
  
          document.body.classList.remove('modal-open');
          modal.remove();
          history.replaceState({ }, document.title, '#');
          window.scrollTo({ top: currentHeight, left: window.scrollX, behaviour: 'instant'});
        },
      };
  
      return this.dialogue;
    }

    #createGridTable(concept_data) {
      const transformedData = concept_data.map(concept =>{
        return [
            `${concept.details.phenotype_owner}/${concept.details.phenotype_owner_history_id}/${concept.concept_id} - ${concept.details.name}`
        ];
    });

      const table = new gridjs.Grid({
        columns: ['Concept', 'Attribute value'],
        data: transformedData
      });
      table.render(document.getElementById('tab-content'));

    }
  
    /**
     * renderView
     * @desc renders the given view
     * @param {enum|int} view the view to render within the active dialogue
     */
    #renderView(view) {
      if (!this.isOpen()) {
        return;
      }
      
      if (!this.options.allowMultiple && view == CSEL_VIEWS.SELECTION) {
        view = CSEL_VIEWS.ATTRIBUTE_TABLE;
      }
      this.dialogue.view = view;
  
      const content = this.dialogue?.content;
      if (!isNullOrUndefined(content)) {
        content.innerHTML = '';
      }
  
      if (this.options.allowMultiple) {
        this.#pushActiveTab(view);
      }
  
      switch (view) {
        case CSEL_VIEWS.ATTRIBUTE_TABLE: {
          this.#createGridTable(this.options.concept_data)
        } break;
  
        case CSEL_VIEWS.SELECTION: {
          this.#renderSelectionView();
        } break;
  
        default: break;
      }
    }
  

  
    /**
     * renderSelectionView
     * @desc renders the selection view where users can manage their currently selected concepts
     */
    #renderSelectionView() {
      // Draw page
      let html = interpolateString(CSEL_INTERFACE.SELECTION_VIEW, {
        noneSelectedMessage: this.options?.noneSelectedMessage,
      });
    
      let doc = parseHTMLFromString(html);
      let page = this.dialogue.content.appendChild(doc.body.children[0]);
      this.dialogue.page = page;

      this.#paintSelectionAttributes();
  
    }
  
    /**
     * pushActiveTab
     * @desc updates the tab view objects when allowMultiple flag is true
     * @param {int|enum} view an enum of CSEL_VIEWS
     */
    #pushActiveTab(view) {
      let tabs = this.dialogue.element.querySelectorAll('button.tab-view__tab');
      for (let i = 0; i < tabs.length; ++i) {
        let tab = tabs[i];
        let relative = tab.getAttribute('id');
        if (!CSEL_VIEWS.hasOwnProperty(relative)) {
          continue;
        }
  
        relative = CSEL_VIEWS[relative];
        if (relative == view) {
          tab.classList.add('active');
        } else {
          tab.classList.remove('active');
        }
      }
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
        'selectionUpdate',
        {
          detail: {
            type: CSEL_EVENTS.CANCELLED,
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
  
      const data = this.dialogue?.data;
      const event = new CustomEvent(
        'selectionUpdate',
        {
          detail: {
            data: data,
            type: CSEL_EVENTS.CONFIRMED,
          }
        }
      );
      this.dialogue?.element.dispatchEvent(event);
    }
  
    /**
     * changeTabView
     * @desc handles the tab buttons
     * @param {event} e the assoc. event
     */
    #changeTabView(e) {
      const target = e.target;
      const desired = target.getAttribute('id');
      if (target.classList.contains('active')) {
        return;
      }
  
      if (!desired || !CSEL_VIEWS.hasOwnProperty(desired)) {
        return;
      }
  
      this.#renderView(CSEL_VIEWS[desired]);
    }

    #paintSelectionAttributes() {
      const page = this.dialogue.page;
      const selectedData = this.dialogue?.data;
      console.log(selectedData)
      if (!this.dialogue?.view == CSEL_VIEWS.SELECTION || isNullOrUndefined(page)) {
        return;
      }
  
      const content = page.querySelector('#item-list');
      const noneAvailable = page.querySelector('#no-items-selected');
      if (isNullOrUndefined(content) || isNullOrUndefined(noneAvailable)) {
        return;
      }
  
      const hasSelectedItems = !isNullOrUndefined(selectedData) && selectedData.length > 0;
  
      // Display none available if no items selected
      if (!hasSelectedItems) {
        content.classList.add('hide');
        noneAvailable.classList.add('show');
        return;
      }
    }
  

  }
  