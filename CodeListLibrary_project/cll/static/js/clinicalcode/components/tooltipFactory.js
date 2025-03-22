/**
 * @class Tooltip Factory
 * @desc Instantiable tooltip factory that handles tooltips for nodes
 *       that require absolute positioning
 * 
 *       The factory is accessible through the window object via window.TooltipFactory
 * 
 * e.g.
  ```js
    window.TooltipFactory.addElement(
      // the element to observe
      document.querySelector('.some-element'),

      // the tooltip text
      'the tip for this element',

      // the direction of the tooltip
      'right'
    );
  ```
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
   * addElement
   * @desc adds a tooltip to an element
   * @param {node}   elem      the element we wish to observe
   * @param {string} tip       optionally specify the tooltip to present to the client; defaults to data attribute of name `data-tipcontent` if not specified
   * @param {string} direction optionally specify the direction of the tooltip when active [right, left, up, down]; defaults to `data-tipdirection` if not specified, or `right` if that fails
   */
  addElement(elem, tip = null, direction = null) {
    let trg = elem.getAttribute('data-tiptarget');
    if (trg === 'parent') {
      trg = elem.parentNode;
    } else {
      trg = elem;
    }

    const uuid = generateUUID();
    trg.setAttribute('data-tooltip', uuid);

    if (typeof tip !== 'string') {
      tip = elem.getAttribute('data-tipcontent');
    }

    tip = strictSanitiseString(tip);
    if (!stringHasChars(tip)) {
      return;
    }

    if (typeof direction !== 'string') {
      direction = elem.getAttribute('data-tipdirection');
      direction = stringHasChars(direction) ? direction : 'right';
    }

    let tooltip = this.#createTooltip(tip, direction);
    tooltip = this.element.appendChild(tooltip);
    tooltip.style.setProperty('display', 'none');

    this.#tooltips[uuid] = tooltip;

    const showTooltip = () => {
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

      const rect = trg.getBoundingClientRect();
      switch (direction) {
        case 'up': {
          tooltip.style.left = `${rect.left + rect.width / 2}px`;
          tooltip.style.top = `${rect.top + height / 2 + height / 4}px`;
        } break;

        case 'down': {
          tooltip.style.left = `${rect.left + rect.width / 2}px`;
          tooltip.style.top = `${rect.top + rect.height / 2 - height / 4}px`;
        } break;

        case 'right': {
          tooltip.style.left = `${rect.left + rect.width}px`;
          tooltip.style.top = `${rect.top + rect.height / 2 - height / 4}px`;
        } break;

        case 'left': {
          tooltip.style.left = `${rect.left}px`;
          tooltip.style.top = `${rect.top + rect.height / 2 - height / 4}px`;
        } break;

        default: {
          tooltip.style.left = `${rect.left + rect.width / 2}px`;
          tooltip.style.top = `${rect.top + rect.height - height / 4}px`;
        } break;
      }
    };

    const hideTooltip = () => {
      if (!isNullOrUndefined(tooltip)) {
        window.removeEventListener('focusout', blurTooltip, { once: true });
        window.removeEventListener('pointermove', blurTooltip, { once: true });
        window.removeEventListener('resize', blurTooltip, { once: true });

        tooltip.style.setProperty('display', 'none');
      }
    };

    const blurTooltip = (e) => {
      const type = (!!e && typeof e === 'object' && 'type' in e) ? e.type : null;
      if (type !== 'focusout' && document.activeElement === this.focusElement) {
        document.activeElement.blur();
      }

      hideTooltip();
    };

    const methods = {
      longpress: (e) => {
        if (e.pointerType !== 'touch') {
          return;
        }

        e.preventDefault();

        showTooltip();

        this.focusElement.focus();
        window.addEventListener('resize', blurTooltip, { once: true });
        window.addEventListener('focusout', blurTooltip, { once: true });
        window.addEventListener('pointerdown', blurTooltip, { once: true });
      },
      enter: () => showTooltip(),
      leave: () => hideTooltip(),
    };
    this.#handlers[uuid] = methods;

    trg.addEventListener('mouseenter', methods.enter);
    trg.addEventListener('mouseleave', methods.leave);
    trg.addEventListener('contextmenu', methods.longpress);
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
      elem.removeEventListener('contextmenu', methods.longpress);
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

    const focusElem = document.createElement('input');
    focusElem.setAttribute('id', 'ctx-focusable');
    focusElem.setAttribute('type', 'text');
    focusElem.setAttribute('aria-live', 'off');
    focusElem.setAttribute('aria-hidden', 'true');
    focusElem.style.display = 'block';
    focusElem.style.position = 'absolute';
    focusElem.style.width = '0';
    focusElem.style.height = '0';
    focusElem.style.opacity = 0;
    focusElem.style.overflow = 'hidden';

    this.element.appendChild(focusElem);
    this.focusElement = focusElem;

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
      className: 'tooltip-container__item',
      innerHTML: {
        src: `<span tooltip="${tip}" direction="${direction}" class="force-active"></span>`,
        noSanitise: true,
      }
    });

    return container;
  }
}

domReady.finally(() => {
  window.TooltipFactory = new TooltipFactory();
});
