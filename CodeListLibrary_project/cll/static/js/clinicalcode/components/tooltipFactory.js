/**
 * @class Tooltip Factory
 * @desc Instantiable tooltip factory that handles tooltips for nodes
 *       that require absolute positioning
 * 
 *       The factory is accessible through the window object via window.TooltipFactory
 * 
 * e.g.
 * ```js
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
 * ```
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
    tooltip.style.setProperty('display', 'none');

    this.#tooltips[uuid] = tooltip;

    const methods = {
      enter: (e) => {
        if (isNullOrUndefined(tooltip)) {
          return;
        }
        tooltip.style.setProperty('display', 'block');

        let span = tooltip.querySelector('span');
        let height = window.getComputedStyle(span, ':after').getPropertyValue('height');
        height = height.matchAll(/(\d+)px/gm);
        height = Array.from(height, x => parseInt(x[1]))
                      .filter(x => !isNaN(x))
                      .shift();
        height = height || 0;

        const rect = elem.getBoundingClientRect();
        switch (direction) {
          case 'up': {
            tooltip.style.left = `${rect.left + rect.width / 2}px`;
            tooltip.style.top = `${rect.top + height / 2}px`;
          } break;
          case 'down': {
            tooltip.style.left = `${rect.left + rect.width / 2}px`;
            tooltip.style.top = `${rect.top + rect.height - height / 4}px`;
          } break;
          case 'right': {
            tooltip.style.left = `${rect.left + rect.width}px`;
            tooltip.style.top = `${rect.top + rect.height - height / 4}px`;
          } break;
          case 'left': {
            tooltip.style.left = `${rect.left}px`;
            tooltip.style.top = `${rect.top + rect.height - height / 4}px`;
          } break;
          default: {
            tooltip.style.left = `${rect.left + rect.width / 2}px`;
            tooltip.style.top = `${rect.top + rect.height - height / 4}px`;
          } break;
        }
      },
      leave: (e) => {
        if (isNullOrUndefined(tooltip)) {
          return;
        }
        tooltip.style.setProperty('display', 'none');
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
