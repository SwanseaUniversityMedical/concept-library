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

  concept_data: null,

  // Allow more than a single Concept to be selected
  allowMultiple: true,

  // Whether to remember the selection when previously opened
  //  [!] Note: Only works when allowMultiple flag is set to true
  maintainSelection: true,

  // Flag to determine whether we scroll to the top of the result page when pagination occurs
  scrollOnResultChange: true,

  // The title of the prompt
  promptTitle: "Import Concepts",

  // The confirm button text
  promptConfirm: "Confirm",

  // The cancel button text
  promptCancel: "Cancel",

  // The size of the prompt (ModalFactory.ModalSizes.%s, i.e., {sm, md, lg})
  promptSize: "lg",

  // The message shown when no items are selected
  noneSelectedMessage: "You haven't selected any attributes yet",
};

/**
 * CSEL_BUTTONS
 * @desc The styleguide for the prompt's buttons
 */
const CSEL_BUTTONS = {
  CONFIRM:
    '<button class="primary-btn text-accent-darkest bold secondary-accent" aria-label="Confirm" id="confirm-button"></button>',
  CANCEL:
    '<button class="secondary-btn text-accent-darkest bold washed-accent" aria-label="Cancel" id="reject-button"></button>',
};

const CSEL_UTILITY_BUTTONS = {
  DELETE_BUTTON:
    '<button class="fill-accordian__label__delete-icon" id="children-button-${id}" type="button" aria-label="Delete"></button> ',
};

/**
 * CSEL_INTERFACE
 * @desc defines the HTML used to render the selection interface
 */
const CSEL_INTERFACE = {
  // Main dialogue modal
  DIALOGUE:
    ' \
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
  TAB_VIEW:
    ' \
    <div class="tab-view" id="tab-view"> \
      <div class="tab-view__tabs tab-view__tabs-z-buffer"> \
        <button aria-label="tab" id="ATTRIBUTE_TABLE" class="tab-view__tab active">Attributed Concepts</button> \
        <button aria-label="tab" id="SELECTION" class="tab-view__tab">All attributes</button> \
      </div> \
      <div class="tab-view__content" id="tab-content"> \
      </div> \
    </div>',

  SELECTION_VIEW:
    ' \
    <div class="detailed-input-group fill no-margin"> \
      <div class="detailed-input-group__header"> \
       <button class="secondary-btn text-accent-darkest bold icon secondary-accent" style="margin-bottom:0.5rem" id="add-attribute-btn">Add attribute +</button> \
      </div> \
      <section class="detailed-input-group__none-available" id="no-items-selected"> \
        <div class="detailed-input-group"> \
        <p class="detailed-input-group__none-available-message">${noneSelectedMessage}</p> \
         </div> \
      </section> \
      <fieldset class="code-search-group indented scrollable slim-scrollbar" id="item-list"> \
      </fieldset> \
    </div>',

  ATTRIBUTE_ACCORDIAN:
    ' \
    <div class="fill-accordian" id="attribute-accordian-${id}" style="margin-top: 0.5rem"> \
    <input class="fill-accordian__input" id="children-${id}" name="children-${id}" type="checkbox" /> \
    <label class="fill-accordian__label" id="children-label-${id}" for="children-${id}" role="button" tabindex="0"> \
      ${title} \
    </label> \
    <article class="fill-accordian__container" id="data" style="padding: 0.5rem;"> \
      ${content} \
    </article> \
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

  constructor(options) {
    this.options = mergeObjects(options || {}, CSEL_OPTIONS);
    this.attribute_component = options.attribute_component;

    this.temporarly_concept_data = JSON.parse(
      JSON.stringify(options.concept_data)
    );

    this.temporarly_concept_data.forEach((concept) => {
      if (concept.attributes) {
        concept.attributes.forEach((attribute) => {
          const uuid = this.#generateUUID();
          attribute.id = uuid;
          attribute.type = this.#typeDeconversion(attribute.type);
        });
      }
    });

    if (!this.options.concept_data[0].attributes) {
      this.attribute_data = [];
    } else {
      this.attribute_data = [];

      this.temporarly_concept_data[0].attributes.forEach((attribute) => {
        this.attribute_data.push({
          id: attribute.id,
          name: attribute.name,
          type: attribute.type,
        });
      });
    }
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
    /**
     * getSelection
     * @desc gets the currently selected concepts
     * @returns {array} the assoc. data
     */
  getAttributeData() {
    return this.attribute_data;
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

    return !!this.dialogue.data.find((item) => {
      return item.id == childId && item.history_id == childVersion;
    });
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
    params = params || {};

    // Reject immediately if we currently have a dialogue open
    if (this.dialogue) {
      return Promise.reject();
    }

    return new Promise((resolve, reject) => {
      this.#buildDialogue(params);
      this.#renderView(view);
      this.#createGridTable(this.temporarly_concept_data);

      this.dialogue.element.addEventListener("selectionUpdate", (e) => {
        this.close();

        const detail = e.detail;
        const eventType = detail.type;
        const data = detail.data;
        switch (eventType) {
          case CSEL_EVENTS.CONFIRMED:
            {
              if (
                this.options.allowMultiple &&
                this.options.maintainSelection
              ) {
                this.attribute_data = data;
              }

              if (this.options.allowMultiple) {
                resolve(data);
                return;
              }
              resolve(data?.[0]);
            }
            break;

          case CSEL_EVENTS.CANCELLED:
            {
              reject();
            }
            break;

          default:
            break;
        }
      });

      this.dialogue.show();
    });
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
      hidden: "false",
    });

    let doc = parseHTMLFromString(html);
    let modal = document.body.appendChild(doc.body.children[0]);

    // create footer
    let footer = createElement("div", {
      id: "target-modal-footer",
      class: "target-modal__footer",
    });

    const container = modal.querySelector(".target-modal__container");
    footer = container.appendChild(footer);

    // create buttons
    const buttons = {};
    let confirmBtn = parseHTMLFromString(CSEL_BUTTONS.CONFIRM);
    confirmBtn = footer.appendChild(confirmBtn.body.children[0]);
    confirmBtn.innerText = this.options.promptConfirm;

    let cancelBtn = parseHTMLFromString(CSEL_BUTTONS.CANCEL);
    cancelBtn = footer.appendChild(cancelBtn.body.children[0]);
    cancelBtn.innerText = this.options.promptCancel;

    buttons["confirm"] = confirmBtn;
    buttons["cancel"] = cancelBtn;

    // initiate main event handling
    buttons?.confirm.addEventListener("click", this.#handleConfirm.bind(this));
    buttons?.cancel.addEventListener("click", this.#handleCancel.bind(this));

    // create content handler
    const body = container.querySelector("#target-modal-content");
    if (this.options?.allowMultiple) {
      body.classList.add("target-modal__body--no-pad");
      body.classList.add("target-modal__body--constrained");
    }

    let contentContainer = body;
    if (this.options.allowMultiple) {
      html = CSEL_INTERFACE.TAB_VIEW;
      doc = parseHTMLFromString(html);
      contentContainer = body.appendChild(doc.body.children[0]);

      const tabs = contentContainer.querySelectorAll("button.tab-view__tab");
      for (let i = 0; i < tabs.length; ++i) {
        tabs[i].addEventListener("click", this.#changeTabView.bind(this));
      }

      contentContainer = contentContainer.querySelector("#tab-content");
    }

    // build dialogue
    this.dialogue = {
      // data
      data: this.options?.maintainSelection ? this.attribute_data : [],
      params: params,
      view: CSEL_VIEWS.ATTRIBUTE_TABLE,

      // dialogue elements
      element: modal,
      buttons: buttons,
      content: contentContainer,

      // dialogue methods
      show: () => {
        createElement("a", { href: `#${this.id}` }).click();
        window.scrollTo({
          top: currentHeight,
          left: window.scrollX,
          behaviour: "instant",
        });

        // inform screen readers of alert
        modal.setAttribute("aria-hidden", false);
        modal.setAttribute("role", "alert");
        modal.setAttribute("aria-live", true);

        // stop body scroll
        document.body.classList.add("modal-open");
      },
      close: () => {
        this.dialogue = null;

        document.body.classList.remove("modal-open");
        modal.remove();
        history.replaceState({}, document.title, "#");
        window.scrollTo({
          top: currentHeight,
          left: window.scrollX,
          behaviour: "instant",
        });
      },
    };

    return this.dialogue;
  }

  #createGridTable(concept_data) {
    document.getElementById("tab-content").innerHTML = "";

    const table = new gridjs.Grid({
      columns: ["Concept"],
      data: concept_data.map((concept) => [
        `${concept.details.phenotype_owner}/${concept.details.phenotype_owner_history_id}/${concept.concept_id} - ${concept.details.name}`,
      ]),
    }).render(document.getElementById("tab-content"));

    if (!concept_data.every((concept) => !concept.attributes)) {
      const transformedData = [];
      for (let i = 0; i < concept_data.length; i++) {
        const concept = concept_data[i];
        const rowData = [
          `${concept.details.phenotype_owner}/${concept.details.phenotype_owner_history_id}/${concept.concept_id} - ${concept.details.name}`,
        ];
        if (concept.attributes) {
          for (let j = 0; j < concept.attributes.length; j++) {
            let attribute = concept.attributes[j];
            attribute.attributes = (cell) => {
              if (cell) {
                return {
                  style: "cursor: pointer",
                  contenteditable: true,
                };
              }
            };
            rowData.push(concept.attributes[j].value);
          }
        }
        transformedData.push(rowData);
      }
      const columns = ["Concept"];
      if (concept_data[0].attributes) {
        concept_data[0].attributes.forEach((attribute) => {
          columns.push(attribute);
        });
      }

      table
        .updateConfig({
          columns: columns,
          data: transformedData,
        })
        .forceRender();
      console.log(columns);
    }
  }

  #addCellEditListeners(tableElement) {
    const rows = tableElement.querySelector("tbody").childNodes;

    const changedCell = [];
    for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
      const row = rows[rowIndex];
      const columns = row.querySelectorAll("td");

      for (let columnIndex = 1; columnIndex < columns.length; columnIndex++) {
        // Skip the first column (Concept)
        const tempCol = columns[columnIndex];
        if (tempCol.innerText !== "") {
          changedCell.push({
            row: rowIndex,
            column: columnIndex,
            value: tempCol.innerText,
          });
        } else {
          changedCell.push({
            row: rowIndex,
            column: columnIndex,
            value: " ",
          });
        }
      }
    }
    for (let i = 0; i < changedCell.length; i++) {
      const cell = changedCell[i];
      const concept = this.temporarly_concept_data[cell.row];
      concept.attributes[cell.column - 1] = {
        id: concept.attributes[cell.column - 1].id,
        value: cell.value,
        name: concept.attributes[cell.column - 1].name,
        type: concept.attributes[cell.column - 1].type,
      };
    }
  }

  #cellValidation(targetInput, attribute) {
    if (!isNaN(targetInput)) {
      this.#pushToast({
        type: "danger",
        message: "Attribute is number",
      });
      return false;
    }
    return true;
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
      content.innerHTML = "";
    }

    if (this.options.allowMultiple) {
      this.#pushActiveTab(view);
    }

    switch (view) {
      case CSEL_VIEWS.ATTRIBUTE_TABLE:
        {
          this.#createGridTable(this.temporarly_concept_data);
          const tableElement = document.querySelector("#tab-content table");
          if (tableElement) {
            tableElement.addEventListener("input", (e) => {
              this.#addCellEditListeners(tableElement);
            });
          }
        }
        break;

      case CSEL_VIEWS.SELECTION:
        {
          this.#renderSelectionView();
        }
        break;

      default:
        break;
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
    let tabs = this.dialogue.element.querySelectorAll("button.tab-view__tab");
    for (let i = 0; i < tabs.length; ++i) {
      let tab = tabs[i];
      let relative = tab.getAttribute("id");
      if (!CSEL_VIEWS.hasOwnProperty(relative)) {
        continue;
      }

      relative = CSEL_VIEWS[relative];
      if (relative == view) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    }
  }

  /*************************************
   *                                   *
   *               Events              *
   *                                   *
   *************************************/

  /**
   * handleConfirm
   * @desc handles the confirmation btn
   * @param {event} e the assoc. event
   */
  #handleConfirm(e) {
    if (!this.isOpen()) {
      return;
    }

    // Clean up the attributes in concept_data
    this.temporarly_concept_data.forEach((concept) => {
      if (concept.attributes) {
        concept.attributes = concept.attributes.map((attr) => ({
          name: attr.name,
          value: attr.value,
          type: this.#typeConversion(attr.type),
        }));
      }
    });

    this.options.concept_data = JSON.parse(
      JSON.stringify(this.temporarly_concept_data)
    );

    const event = new CustomEvent("selectionUpdate", {
      detail: {
        data: this.options.concept_data,
        type: CSEL_EVENTS.CONFIRMED,
      },
    });
    this.dialogue?.element.dispatchEvent(event);
  }

  /**
   * handleCancel
   * @desc handles the cancel/exit btn
   * @param {event} e the assoc. event
   */
  #handleCancel(e) {
    if (!this.isOpen()) {
      return;
    }

    const event = new CustomEvent("selectionUpdate", {
      detail: {
        type: CSEL_EVENTS.CANCELLED,
      },
    });
    this.dialogue?.element.dispatchEvent(event);
  }

  #generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        var r = (Math.random() * 16) | 0,
          v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      }
    );
  }

  #handleAttributeCreation(e) {
    const page = this.dialogue.page;
    page.querySelector("#add-attribute-btn").setAttribute("disabled", true);
    const noneAvailable = page.querySelector("#no-items-selected");

    let attribute_progress = parseHTMLFromString(this.attribute_component);
    const uniqueId = this.#generateUUID();
    attribute_progress = interpolateString(this.attribute_component, {
      id: uniqueId,
    });

    if (this.attribute_data.length <= 0) {
      let attributerow = interpolateString(CSEL_INTERFACE.ATTRIBUTE_ACCORDIAN, {
        id: uniqueId,
        title: `New attribute value`,
        content: attribute_progress,
      });
      let doc = parseHTMLFromString(attributerow);
      noneAvailable.classList.remove("show");
      page.appendChild(doc.body.children[0]);
    } else {
      let attributerow = interpolateString(CSEL_INTERFACE.ATTRIBUTE_ACCORDIAN, {
        id: uniqueId,
        title: "New attribute value",
        content: attribute_progress,
      });
      let doc = parseHTMLFromString(attributerow);
      page.appendChild(doc.body.children[0]);
    }

    let attribute = {
      id: uniqueId,
      name: "",
      type: "-1",
      value: " ",
    };

    attribute = this.#invokeAttributeInputs(attribute, page);

    this.#invokeAttributeButtons(attribute, page);
  }

  #invokeAttributeButtons(attribute, page) {
    const confirmChanges = page.querySelector(
      "#confirm-changes-" + attribute.id
    );
    confirmChanges.addEventListener("click", () =>
      this.#handleConfirmEditor(attribute)
    );

    const cancelChanges = page.querySelector("#cancel-changes-" + attribute.id);
    cancelChanges.addEventListener("click", () =>
      this.#handleCancelEditor(attribute)
    );

    if (page.querySelector("#children-button-" + attribute.id)) {
      const deleteAttributeButton = page.querySelector(
        "#children-button-" + attribute.id
      );
      deleteAttributeButton.addEventListener("click", () =>
        this.#deleteAttribute(attribute)
      );
    }
  }

  #invokeAttributeInputs(attribute, page) {
    const attribute_name_input = page.querySelector(
      "#attribute-name-input-" + attribute.id
    );
    const attribute_type = page.querySelector(
      "#attribute-type-" + attribute.id
    );

    attribute_type.addEventListener("change", () => {
      attribute.type = attribute_type.value;
    });

    attribute_name_input.addEventListener("input", () => {
      attribute.name = `${attribute_name_input.value}`;
    });

    return attribute;
  }

  #typeConversion(type) {
    switch (type) {
      case "1":
        return "INT";
      case "2":
        return "STRING";
      case "3":
        return "FLOAT";
    }
  }

  #typeDeconversion(type) {
    switch (type) {
      case "INT":
        return "1";
      case "STRING":
        return "2";
      case "FLOAT":
        return "3";
    }
  }

  #deleteAttribute(attribute) {
    const page = this.dialogue.page;

    const accordian = page.querySelector(
      "#attribute-accordian-" + attribute.id
    );

    const noneAvailable = page.querySelector("#no-items-selected");

    const indexToDelete = this.attribute_data.findIndex(
      (attr) => attr.id === attribute.id
    );

    if (indexToDelete !== -1) {
      // Remove the attribute from attribute_data
      this.attribute_data.splice(indexToDelete, 1);

      // Remove the related attributes from concept_data
      this.temporarly_concept_data.forEach((concept) => {
        if (concept.attributes) {
          concept.attributes = concept.attributes.filter(
            (attr) => attr.id !== attribute.id
          );
        }
      });

      // Remove the accordian element
      accordian.remove();

      // Show the "no items selected" message if there are no attributes left
      if (
        this.attribute_data.length <= 0 &&
        page.querySelectorAll(".fill-accordian").length <= 0
      ) {
        noneAvailable.classList.add("show");
      }

      this.#pushToast({
        type: "danger",
        message: "Attribute has been deleted",
      });
    }
  }

  #pushToast({ type = "information", message = null, duration = "5000" }) {
    if (isNullOrUndefined(message)) {
      return;
    }

    window.ToastFactory.push({
      type: type,
      message: message,
      duration: Math.max(duration, "444"),
    });
  }

  #handleConfirmEditor(attribute) {
    // Validate the concept data
    if (!attribute || attribute.name === "") {
      this.#pushToast({
        type: "danger",
        message: "Attribute name cannot be empty",
      });
      return;
    }

    if (attribute.type === "-1") {
      this.#pushToast({ type: "danger", message: "Please select a type" });
      return;
    }

    // Check if the attribute already exists in attribute_data
    const existingAttributeIndex = this.attribute_data.findIndex(
      (attr) => attr.id === attribute.id
    );

    if (existingAttributeIndex !== -1) {
      // Update the existing attribute with the new name and type if they have changed
      const existingAttribute = this.attribute_data[existingAttributeIndex];
      if (
        existingAttribute.name !== attribute.name ||
        existingAttribute.type !== attribute.type
      ) {
        existingAttribute.name = attribute.name;
        existingAttribute.type = attribute.type;
      }
    } else {
      // Add the new attribute to attribute_data if it doesn't exist
      this.attribute_data.push(attribute);
      this.#pushToast({
        type: "success",
        message: "Attribute added successfully",
      });
    }

    // Update the concept_data with the updated attribute
    this.temporarly_concept_data.forEach((concept) => {
      if (!concept.hasOwnProperty("attributes")) {
        concept.attributes = [];
      }
      const existingConceptAttributeIndex = concept.attributes.findIndex(
        (attr) => attr.id === attribute.id
      );
      if (existingConceptAttributeIndex !== -1) {
        // Update the existing attribute in concept.attributes with the new name and type if they have changed
        const existingConceptAttribute =
          concept.attributes[existingConceptAttributeIndex];
        if (
          existingConceptAttribute.name !== attribute.name ||
          existingConceptAttribute.type !== attribute.type
        ) {
          existingConceptAttribute.name = attribute.name;
          existingConceptAttribute.type = attribute.type;
        }
      } else {
        // Add the new attribute to concept.attributes if it doesn't exist
        concept.attributes.push(attribute);
      }
    });

    // Update the accordian label with the new attribute details
    const accordian = this.dialogue.page.querySelector(
      "#attribute-accordian-" + attribute.id
    );
    const accordianLabel = accordian.querySelector(
      "#children-label-" + attribute.id
    );
    let accordianDeleteButton = interpolateString(
      CSEL_UTILITY_BUTTONS.DELETE_BUTTON,
      {
        id: attribute.id,
      }
    );
    const deleteButtonElement = parseHTMLFromString(accordianDeleteButton).body
      .children[0];
    accordianLabel.textContent = "";
    accordianLabel.insertBefore(deleteButtonElement, accordianLabel.firstChild);
    accordianLabel.appendChild(
      document.createTextNode(
        ` ${attribute.name} - ${this.#typeConversion(attribute.type)}`
      )
    );

    // Close the accordian and re-enable the add attribute button
    accordianLabel.click();
    this.dialogue.page
      .querySelector("#add-attribute-btn")
      .removeAttribute("disabled");

    this.dialogue.page
      .querySelector("#children-button-" + attribute.id)
      .addEventListener("click", () => {
        this.#deleteAttribute(attribute);
      });
  }

  #handleCancelEditor(attribute) {
    const page = this.dialogue.page;
    const attribute_name_input = page.querySelector(
      "#attribute-name-input-" + attribute.id
    );
    const attribute_type = page.querySelector(
      "#attribute-type-" + attribute.id
    );
    const accordian = page.querySelector(
      "#attribute-accordian-" + attribute.id
    );
    const noneAvailable = page.querySelector("#no-items-selected");

    if (this.attribute_data.length <= 0) {
      attribute_name_input.value = null;
      attribute_type.value = -1;
      accordian.remove();
      noneAvailable.classList.add("show");
      page.querySelector("#add-attribute-btn").removeAttribute("disabled");
    } else {
      if (attribute_name_input.value === "" || attribute_type.value === "-1") {
        accordian.remove();
        page.querySelector("#add-attribute-btn").removeAttribute("disabled");
      }
      accordian.querySelector("#children-label-" + attribute.id).click();
    }
  }

  /**
   * changeTabView
   * @desc handles the tab buttons
   * @param {event} e the assoc. event
   */
  #changeTabView(e) {
    const target = e.target;
    const desired = target.getAttribute("id");
    if (target.classList.contains("active")) {
      return;
    }

    if (!desired || !CSEL_VIEWS.hasOwnProperty(desired)) {
      return;
    }

    this.#renderView(CSEL_VIEWS[desired]);
  }

  #paintSelectionAttributes() {
    console.log(this.attribute_data);
    const page = this.dialogue.page;
    if (
      !this.dialogue?.view == CSEL_VIEWS.SELECTION ||
      isNullOrUndefined(page)
    ) {
      return;
    }

    const content = page.querySelector("#item-list");
    const noneAvailable = page.querySelector("#no-items-selected");
    if (isNullOrUndefined(content) || isNullOrUndefined(noneAvailable)) {
      return;
    }

    const hasSelectedItems =
      !isNullOrUndefined(this.attribute_data) && this.attribute_data.length > 0;

    // Display none available if no items selected
    let addAttributeButton = page.querySelector("#add-attribute-btn");
    if (!hasSelectedItems) {
      content.classList.add("hide");
      noneAvailable.classList.add("show");

      if (addAttributeButton) {
        addAttributeButton.addEventListener("click", () => {
          this.#handleAttributeCreation(this);
        });
      }
      return;
    } else {
      content.classList.remove("hide");
      noneAvailable.classList.remove("show");

      for (let i = 0; i < this.attribute_data.length; ++i) {
        let attribute = this.attribute_data[i];
        let attribute_progress = interpolateString(this.attribute_component, {
          id: attribute.id,
        });

        attribute_progress = parseHTMLFromString(attribute_progress);

        attribute_progress
          .querySelector("#attribute-name-input-" + attribute.id)
          .setAttribute("value", attribute.name);
        attribute_progress
          .querySelector("#attribute-type-" + attribute.id)
          .querySelector(`option[value="${attribute.type}"]`)
          .setAttribute("selected", true);

        let attributerow = interpolateString(
          CSEL_INTERFACE.ATTRIBUTE_ACCORDIAN,
          {
            id: attribute.id,
            title: `${attribute.name} - ${this.#typeConversion(
              attribute.type
            )}`,
            content: attribute_progress.body.outerHTML,
          }
        );

        let doc = parseHTMLFromString(attributerow);

        const accordianLabel = doc.querySelector(
          "#children-label-" + attribute.id
        );
        let accordianDeleteButton = interpolateString(
          CSEL_UTILITY_BUTTONS.DELETE_BUTTON,
          {
            id: attribute.id,
          }
        );
        const deleteButtonElement = parseHTMLFromString(accordianDeleteButton)
          .body.children[0];
        accordianLabel.textContent = "";
        accordianLabel.insertBefore(
          deleteButtonElement,
          accordianLabel.firstChild
        );
        accordianLabel.appendChild(
          document.createTextNode(
            `${attribute.name} - ${this.#typeConversion(attribute.type)}`
          )
        );

        page.appendChild(doc.body.children[0]);

        attribute = this.#invokeAttributeInputs(attribute, page);
        this.#invokeAttributeButtons(attribute, page);
      }
      if (addAttributeButton) {
        addAttributeButton.addEventListener("click", () => {
          this.#handleAttributeCreation(this);
        });
      }
    }
  }
}
