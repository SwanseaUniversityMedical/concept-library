
/**
 * Tooltip Factory
 * @desc Instantiable tooltip factory that handles tooltips for nodes
 *       that require absolute positioning
 * 
 *       The factory is accessible through the window object via window.TooltipFactory
 * 
 * e.g.
 *    window.TooltipFactory.addTooltip(
 *      // the element to observe
 *      document.querySelector('.some-element'),
 * 
 *      // the tooltip text
 *      'the tip for this element',
 * 
 *      // the direction of the tooltip
 *      'right'
 *    );
 */
class TooltipFactory {
  #handlers = {};
  #tooltips = {};

  constructor() {
    this.#createContainer();
  }

  /*************************************
   *                                   *
   *               Getter              *
   *                                   *
   *************************************/
  /**
   * getElement
   * @returns {node} the container element assoc. with this factory
   */
  getElement() {
    return this.element;
  }

  /*************************************
   *                                   *
   *               Setter              *
   *                                   *
   *************************************/
  /**
   * addTooltip
   * @desc adds a tooltip to an element
   * @param {node} elem the element we wish to observe
   * @param {string} tip the tooltip to present to the client
   * @param {string} direction the direction of the tooltip when active [right, left, up, down]
   */
  addTooltip(elem, tip, direction) {
    const uuid = generateUUID();
    elem.setAttribute('data-tooltip', uuid);

    let tooltip = this.#createTooltip(tip, direction);
    tooltip = this.element.appendChild(tooltip);
    tooltip.classList.add('hide');

    this.#tooltips[uuid] = tooltip;

    const methods = {
      enter: (e) => {
        if (isNullOrUndefined(tooltip)) {
          return;
        }
        tooltip.classList.remove('hide');

        const rect = elem.getBoundingClientRect();
        tooltip.style.left = `${rect.left}px`
        tooltip.style.top = `${rect.top + 20}px`;
      },
      leave: (e) => {
        if (isNullOrUndefined(tooltip)) {
          return;
        }
        tooltip.classList.add('hide');
      },
    };
    this.#handlers[uuid] = methods;

    elem.addEventListener('mouseenter', methods.enter);
    elem.addEventListener('mouseleave', methods.leave);
  }

  /**
   * clearTooltips
   * @desc clears the tooltips that relate to an element
   * @param {*} elem the node with an active tooltip
   */
  clearTooltips(elem) {
    if (isNullOrUndefined(elem)) {
      return;
    }

    const uuid = elem.getAttribute('data-tooltip');
    if (isNullOrUndefined(uuid)) {
      return;
    }

    const tooltip = this.#tooltips[uuid];
    if (!isNullOrUndefined(tooltip)) {
      this.element.removeChild(tooltip);
    }
    this.#tooltips[uuid] = null;

    const methods = this.#handlers[uuid];
    if (!isNullOrUndefined(methods)) {
      elem.removeEventListener('mouseenter', methods.enter);
      elem.removeEventListener('mouseleave', methods.leave);
    }
    this.#handlers[uuid] = null;

    elem.removeAttribute('data-tooltip');
  }

  /*************************************
   *                                   *
   *               Render              *
   *                                   *
   *************************************/
  /**
   * createContainer
   * @desc initialisation method to create the tooltip container
   */
  #createContainer() {
    this.element = createElement('div', {
      className: 'tooltip-container',
    });

    document.body.prepend(this.element);
  }

  /**
   * createTooltip
   * @desc creates the tooltip element that will be appended/removed during mouse eventsd
   * @param {string} tip the tooltip text
   * @param {string} direction the direction of the tooltip
   */
  #createTooltip(tip, direction) {
    const container = createElement('div', {
      'className': 'tooltip-container__item',
      'innerHTML': `<span tooltip="${tip}" direction="${direction}" class="force-active"></span>`
    });

    return container;
  }
}

domReady.finally(() => {
  window.TooltipFactory = new TooltipFactory();
});
