import * as Const from './constants.js';

import { managePlugins } from './plugins.js';
import { manageNavigation } from './navigation.js';
import { managePopoverMenu } from './popoverMenu.js';

/**
 * Todo:
 *  1. Page state
 *    -> TODO:
 *      -> Finalise `get_asset_rules()` implementation
 *      -> Attempt `Overview`, then move to other Targets/Pages
 * 
 *  2. Renderables
 *    -> Views: collect from Model method?
 *    -> Forms: use admin forms, e.g. TemplateForm?
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
  /**
   * @desc
   * @type {string}
   * @static
   * @constant
   */
  static #UrlPath = 'dashboard';

  /**
   * @desc default constructor props
   * @type {Record<string, any>}
   * @static
   * @constant
   * 
   * @property {string}             [page='overview'] Page to open on initialisation
   * @property {string}             [view]            View to open on initialisation
   * @property {*}                  [target]          Entity to target on initialisation
   * @property {string|HTMLElement} [element='#app']  The root app element in which to render the service
   */
  static #DefaultOpts = {
    page: 'overview',
    view: null,
    target: null,
    element: '#app',
    token: null,
  };

  /**
   * @desc
   * @public
   */
  element = null;

  /**
   * @desc
   * @private
   */
  #state = {
    initialised: false,
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
   * @desc
   * @type {Array<Function>}
   * @private
   */
  #disposables = [];

  /**
   * @param {Record<string, any>} [opts] constructor arguments; see {@link DashboardService.#DefaultOpts}
   */
  constructor(opts = null) {
    opts = isRecordType(opts) ? opts : { };
    opts = mergeObjects(opts, DashboardService.#DefaultOpts, true);

    this.#initialise(opts);
  }

  /*************************************
   *                                   *
   *              Public               *
   *                                   *
   *************************************/
  openPage(page, view = null, target = null) {
    const state = this.#state;
    if (state.page === page && state.view === view && state.target === target && state.initialised) {
      return;
    }

    let hnd;
    switch (page) {
      case 'overview':
        hnd = this.#renderOverview;
        break;

      case 'users':
        hnd = this.#renderUsers;
        break;

      case 'organisations':
        hnd = this.#renderOrganisations;
        break;

      case 'inventory':
        hnd = this.#renderInventory;
        break;

      case 'brand-config':
        hnd = this.#renderBrand;
        break;
      
      default:
        break;
    }

    if (hnd) {
      state.page = page;
      state.view = view;
      state.target = target;
      state.initialised = true;
      this.#toggleNavElement(page);
      hnd.apply(this);
    }
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
  #getTargetUrl(
    target,
    {
      view = 'view',
      kwargs = null,
      parameters = null,
      useBranded = true,
    } = {}
  ) {
    view = view.toLowerCase();

    if (parameters instanceof URLSearchParams) {
      parameters = '?' + parameters;
    } else if (isObjectType(parameters)) {
      parameters = '?' + new URLSearchParams(parameters);
    } else if (typeof parameters !== 'string') {
      parameters = '';
    }

    const host = useBranded ? getBrandedHost() : getCurrentHost();
    const root = host + '/' + DashboardService.#UrlPath;
    switch (view) {
      case 'view':
        return `${root}/${target}/` + parameters;

      case 'list':
        return `${root}/target/${target}/` + parameters;

      case 'display':
        return `${root}/target/${target}/${kwargs}/` + parameters;

      default:
        return null
    }
  }

  #fetch(url, opts = {}) {
    const token = this.#state.token;
    opts = mergeObjects(
      {
        method: 'GET',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      },
      isObjectType(opts) ? opts : {},
      false,
      true
    );

    return fetch(url, opts);
  }


  /*************************************
   *                                   *
   *            Renderables            *
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

  #clearContent() {
    this.#layout.content.replaceChildren();
  }

  #renderOverview() {
    const state = this.#state;
    this.#clearContent();

    const [activity] = composeTemplate(this.#templates.base.group, {
      params: {
        id: 'activity',
        title: 'Activity',
        level: '1',
        articleCls: 'dashboard-view__content--fill-w',
        sectionCls: 'dashboard-view__content-grid slim-scrollbar',
        content: '',
      },
      parent: this.#layout.content,
    });

    const [quickAccess] = composeTemplate(this.#templates.base.group, {
      params: {
        id: 'quick-access',
        title: 'Quick Access',
        level: '2',
        articleCls: 'dashboard-view__content--fill-w',
        sectionCls: 'dashboard-view__content-grid slim-scrollbar',
        content: '',
      },
      parent: this.#layout.content,
    });

    let spinners;
    let spinnerTimeout = setTimeout(() => {
      spinners = {
        activity: startLoadingSpinner(activity, true),
        quickAccess: startLoadingSpinner(quickAccess, true),
      };
    }, 200);

    const url = this.#getTargetUrl('stats-summary');
    this.#fetch(url, { method: 'GET' })
      .then(res => {
        if (!spinners) {
          clearTimeout(spinnerTimeout);
        }

        return res.json();
      })
      .then(res => {
        const stats = res.summary.data;
        const statsTimestamp = new Date(Date.parse(res.summary.timestamp));

        const [statsDatetime] = composeTemplate(this.#templates.base.time, {
          params: {
            datefmt: statsTimestamp.toLocaleString(),
            timestamp: statsTimestamp.toISOString(),
          }
        });

        const activityContent = activity.querySelector('section');
        for (let key in stats) {
          const details = Const.ACTIVITY_CARDS.find(x => x.key === key);
          if (!details) {
            continue;
          }

          composeTemplate(this.#templates.base.display_card, {
            params: {
              name: details.name,
              desc: details.desc,
              icon: details.icon,
              iconCls: details.iconCls,
              content: `<figure class="card__data">${stats[key].toLocaleString()}</figure>`,
              footer: statsDatetime.outerHTML,
            },
            parent: activityContent,
          });
        }
        spinners?.activity?.remove?.();

        const assets = res.assets;
        const quickAccessContent = quickAccess.querySelector('section');
        if (isObjectType(assets)) {
          const keys = Object.keys(assets).sort((a, b) => {
            const v0 = assets[a]?.details?.verbose_name ?? '';
            const v1 = assets[b]?.details?.verbose_name ?? '';
            return v0 < v1 ? -1 : (v0 > v1 ? 1 : 0);
          });

          for (let i = 0; i < keys.length; ++i) {
            const key = keys[i];
            const asset = assets[key];
            const details = isObjectType(asset) ? asset?.details : null
            if (!details) {
              continue;
            }

            const [card] = composeTemplate(this.#templates.base.action_card, {
              params: {
                name: details.verbose_name,
                desc: `Manage ${details.verbose_name_plural}`,
                icon: '&#xf1c0;',
                iconCls: 'as-icon--primary',
                action: 'Manage',
              },
              parent: quickAccessContent,
            });

            const button = card.querySelector('[data-role="action-btn"]');
            button.addEventListener('click', (e) => {
              this.openPage('inventory', null, { type: key });
            });
          }
        }
        spinners?.quickAccess?.remove?.();

        if (quickAccessContent.childElementCount < 1) {
          quickAccess.remove();
        }
      })
      .catch(console.error);
  }

  #renderUsers() {
    const state = this.#state;
    const view = state.view ?? 'list';
    const target = state.target;
    this.#clearContent();

    const pageCls = view === 'list' ? 'dashboard-view__content--fill-w' : '';
    const viewCls = view === 'list' ? 'dashboard-view__content-table' : '';

    const [pageArticle] = composeTemplate(this.#templates.base.group, {
      params: {
        id: 'users',
        title: 'Users',
        level: '1',
        articleCls: pageCls,
        sectionCls: viewCls,
        content: '',
      },
      parent: this.#layout.content,
    });

    switch (view) {
      case 'list': {
        const url = this.#getTargetUrl('template', { view: 'list' });

        this.#fetch(url)
          .then(res => res.json())
          .then(res => console.log(res));

        const data = [
          {
            "name": "Unity Pugh",
            "extension": "9958",
            "city": "Curicó",
            "start_date": "2005/02/11"
          },
          {
            "name": "Theodore Duran",
            "extension": "8971",
            "city": "Dhanbad",
            "start_date": "1999/04/07"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Unity Pugh",
            "extension": "9958",
            "city": "Curicó",
            "start_date": "2005/02/11"
          },
          {
            "name": "Theodore Duran",
            "extension": "8971",
            "city": "Dhanbad",
            "start_date": "1999/04/07"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Unity Pugh",
            "extension": "9958",
            "city": "Curicó",
            "start_date": "2005/02/11"
          },
          {
            "name": "Theodore Duran",
            "extension": "8971",
            "city": "Dhanbad",
            "start_date": "1999/04/07"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Unity Pugh",
            "extension": "9958",
            "city": "Curicó",
            "start_date": "2005/02/11"
          },
          {
            "name": "Theodore Duran",
            "extension": "8971",
            "city": "Dhanbad",
            "start_date": "1999/04/07"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Unity Pugh",
            "extension": "9958",
            "city": "Curicó",
            "start_date": "2005/02/11"
          },
          {
            "name": "Theodore Duran",
            "extension": "8971",
            "city": "Dhanbad",
            "start_date": "1999/04/07"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
          {
            "name": "Kylie Bishop",
            "extension": "3147",
            "city": "Norman",
            "start_date": "2005/09/08"
          },
        ];

        const headings = [
          {
            text: "Name",
            data: "name"
          },
          {
            text: "Ext.",
            data: "extension"
          },
          {
            text: "City",
            data: "city"
          },
          {
            text: "Start date",
            data: "start_date"
          }
        ];

        const container = pageArticle.querySelector('section');
        const datatable = new window.simpleDatatables.DataTable(container, {
          perPage: 10,
          perPageSelect: false,
          fixedColumns: true,
          sortable: false,
          labels: {
            perPage: '',
          },
          classes: {
            wrapper: 'overflow-table-constraint',
          },
          columns: [
            { select: 0, type: 'string' },
            { select: 1, type: 'string' },
            { select: 2, type: 'string' },
            { select: 3, type: 'string' },
          ],
          template: (options, dom) => `<div class='${options.classes.top}'>
            <div class='${options.classes.dropdown}'>
              <label>
                <select class='${options.classes.selector}'></select> ${options.labels.perPage}
              </label>
            </div>
            <div class='${options.classes.search}'>
              <input
                id="column-searchbar"
                class='${options.classes.input}'
                type='search'
                placeholder='${options.labels.placeholder}'
                title='${options.labels.searchTitle}'
                ${dom.id ? `aria-controls="${dom.id}"` : ""}>
            </div>
            </div>
            <div class='${options.classes.container}'${options.scrollY.length ? ` style='height: ${options.scrollY}; overflow-Y: auto;'` : ""}></div>
            <div class='${options.classes.bottom}'>
          </div>`,
          data: { headings, data },
          pagerRender: (data, ul) => {
            console.log(data, ul);
            return ul;
          }
        });

        datatable.on('datatable.init', function () {
          setTimeout(() => console.log(this.pagers), 1000);
          console.log(datatable)
        });
        datatable.on('datatable.page', function (page) {
          console.log(page);
        });
      
      } break;

      case 'display':
        break;

      case 'create':
        break;

      case 'update':
        break;

      default:
        break;
    }
  }

  #renderOrganisations() {
    const state = this.#state;
    const view = state.view ?? 'list';
    const target = state.target;
    this.#clearContent();

  }

  #renderInventory() {
    const state = this.#state;
    const view = state.view ?? 'list';
    const target = state.target;
    this.#clearContent();


  }

  #renderBrand() {
    const state = this.#state;
    const view = state.view;
    this.#clearContent();

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

    let token = opts.token;
    if (typeof token !== 'string' || !stringHasChars(token)) {
      token = getCookie('csrftoken');
    }

    this.#state = mergeObjects(this.#state, { page: opts.page, token: token }, false);
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

    // Init render
    this.openPage(this.#state.page);
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
