import * as Const from './constants.js';

import { managePlugins } from './plugins.js';
import { manageNavigation } from './navigation.js';
import { managePopoverMenu } from './popoverMenu.js';

/**
 * Todo:
 *  1. Page state
 * 
 *  2. Overview
 *    -> Activity: render API data
 *    -> Quick Access: Collect known editable data assets editable per brand
 * 
 *  3. People
 *    -> People API fetch & render
 *    -> Ability to create / edit user(s)
 * 
 *  4. Organisations
 *    -> Organisation API fetch & render
 *    -> Ability to create / modify organisation(s)
 * 
 *  5. Brand
 *    -> Brand API fetch & render
 *    -> Modify Brand data
 * 
 *  6. Inventory
 *    -> Allow creation + editing of assets per `Quick Access` view
 *
 */

/**
 * Class to serve & manage Dashboard page content
 * 
 * @class
 * @constructor
 */
export class DashboardService {
  static #DefaultOpts = {
    page: 'overview',
    element: '#app',
  };

  element = null;

  #state = {
    initialised: false,
  };

  #layout = {};
  #templates = {};
  #disposables = [];

  constructor(opts) {
    opts = isRecordType(opts) ? opts : { };
    opts = mergeObjects(opts, DashboardService.#DefaultOpts, true);

    this.#initialise(opts);
  }

  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/
  openPage(target) {
    const state = this.#state;
    if (state.page === target && state.initialised) {
      return;
    }

    state.page = target;
    state.initialised = true;

    console.log('open', '->', target);
  }

  dispose() {
    let disposable;
    for (let i = this.#disposables.length; i > 0; i--) {
      disposable = this.#disposables.pop();
      if (typeof disposable !== 'function') {
        continue;
      }

      disposable();
    }
  }


  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/
  #toggleNavElement(target) {
    const items = this.#layout.nav.querySelectorAll('[data-controlledby="navigation"]');
    for (let i = 0; i < items.length; ++i) {
      const btn = items[i];
      const ref = btn.getAttribute('data-ref');
      btn.setAttribute('data-active', ref === target);
    }
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #eventHandler(e) {
    console.log(e);
  }

  #handleNavigation(e, targetName) {
    this.#toggleNavElement(targetName);
    this.openPage(targetName);
  }

  #handlePopoverMenu(e, _group, _closeHnd) {
    const btn = e.target;

    const link = btn.getAttribute('data-link');
    if (typeof link === 'string') {
      tryNavigateLink(btn, { relatedEvent: e });
    }
  }


  /*************************************
   *                                   *
   *            Initialiser            *
   *                                   *
   *************************************/
  #initialise(opts) {
    let element = opts.element;
    if (typeof element === 'string') {
      element = document.querySelector(element);
    }

    if (!isHtmlObject(element)) {
      throw new Exception('InitError: Failed to resolve DashboardService element');
    }

    this.#state = mergeObjects(this.#state, { page: opts.page }, false);
    this.element = element;
    this.#collectPage();

    // Init event listeners
    const eventHandler = this.#eventHandler.bind(this);
    element.addEventListener('dashboard', eventHandler, false);

    // Initialise managers
    this.#disposables.push(
      manageNavigation({
        parent: element,
        callback: this.#handleNavigation.bind(this),
      }),
      managePlugins({
        parent: element,
        observeMutations: true,
        observeDescendants: true,
      }),
      managePopoverMenu({
        parent: element,
        callback: this.#handlePopoverMenu.bind(this),
      }),
    );

    /* TEMP */
    const token = getCookie('csrftoken');
    fetch('/dashboard/stats-summary', {
      method: 'GET',
      credentials: 'same-origin',
      withCredentials: true,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': token,
        'Authorization': `Bearer ${token}`
      },
    })
      .then(res => res.json())
      .then(console.log)
      .catch(console.error);

    /* TEMP */
    const icon = composeTemplate(this.#templates.base.icon, {
      params: {
        cls: 'as-icon--warning',
        icon: Const.ACTIVITY_CARDS[0].icon,
      }
    })

    const article = composeTemplate(this.#templates.base.group, {
      params: {
        id: 'quick-access',
        title: 'Quick Access',
        level: '2',
        articleCls: 'dashboard-view__content--fill-w',
        sectionCls: 'dashboard-view__content-grid slim-scrollbar',
        content: '',
      },
      modify: [
        {
          select: 'article',
          apply: (elem) => {
            const header = elem.querySelector('h2');
            header.insertAdjacentElement('beforeend', icon[0]);

            startLoadingSpinner(elem, true);
          },
          parent: this.#layout.content,
        },
      ]
    });
  }

  #collectPage() {
    const layout = document.querySelectorAll('[id^="app-"]');
    const templates = document.querySelectorAll('template[data-for="dashboard"]');

    // Collect base layout
    let elem, name;
    for (let i = 0; i < layout.length; ++i) {
      elem = layout[i];
      name = elem.getAttribute('id').replace('app-', '');
      this.#layout[name] = elem;
    }

    // Collect templates
    let view, group;
    for (let i = 0; i < templates.length; ++i) {
      elem = templates[i];
      name = elem.getAttribute('data-name');
      view = elem.getAttribute('data-view');
      if (!stringHasChars(view)) {
        view = 'base';
      }

      group =  this.#templates?.[view];
      if (!group) {
        group = { };
        this.#templates[view] = group;
      }

      group[name] = elem;
    }
  }
};
