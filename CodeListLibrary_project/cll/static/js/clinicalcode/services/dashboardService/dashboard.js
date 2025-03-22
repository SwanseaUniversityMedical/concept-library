import * as Const from './constants.js';

import { managePlugins } from './plugins.js';
import { manageNavigation } from './navigation.js';
import { managePopoverMenu } from './popoverMenu.js';

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

  #state = null;
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

  openPage(pageName) {

  }

  /*************************************
   *                                   *
   *              Private              *
   *                                   *
   *************************************/



  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #eventHandler(e) {
    console.log(e);
  }

  #handleNavigation(e, menuName) {
    console.log(menuName)
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

    this.#state = { page: opts.page };
    this.element = element;
    this.#collectPage();

    // Init event listeners
    const eventHandler = this.#eventHandler.bind(this);
    element.addEventListener('dashboard', eventHandler, false);

    // Initialise managers
    this.#disposables.push(
      manageNavigation(
        this.#handleNavigation.bind(this),
        element
      ),
      managePlugins(element),
      managePopoverMenu(),
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
