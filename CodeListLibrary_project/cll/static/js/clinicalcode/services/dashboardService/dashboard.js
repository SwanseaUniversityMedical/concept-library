import * as Const from './constants.js';

import { FormView } from './views/formView.js';
import { TableView } from './views/tableView.js';
import { managePlugins } from './managers/plugins.js';
import { manageNavigation } from './managers/navigation.js';
import { managePopoverMenu } from '../../components/popoverMenu.js';

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
   * @property {string}             [token=*]         CSRF cookie (auto-filled)
   * @property {*}                  [target]          Entity to target on initialisation
   * @property {string|HTMLElement} [element='#app']  The root app element in which to render the service
   */
  static #DefaultOpts = {
    page: 'overview',
    view: null,
    token: null,
    target: null,
    element: '#app',
  };

  /**
   * @desc
   * @type {HTMLElement}
   * @public
   */
  element = null;

  /**
   * @desc
   * @type {object}
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

      case 'inventory':
        hnd = this.#renderInventory;
        break;

      case 'brand-config':
        hnd = this.#renderBrand;
        break;
      
      default:
        hnd = this.#renderModelView;
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
    const state = this.#state;
    const controller = state?.controller;
    if (controller) {
      controller.dispose();
      delete state.controller;
    }

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
        return `${root}/view/${target}/` + parameters;

      case 'list':
        return `${root}/target/${target}/` + parameters;

      case 'create':
        return `${root}/target/${target}/` + parameters;

      case 'update':
        if (!isNullOrUndefined(kwargs)) {
          return `${root}/target/${target}/${kwargs}/` + parameters;
        }
        return `${root}/target/${target}/` + parameters;

      default:
        return null
    }
  }

  #fetch(url, opts = {}) {
    const token = this.#state.token;
    opts = mergeObjects(
      isObjectType(opts) ? opts : {},
      {
        method: 'GET',
        cache: 'no-cache',
        credentials: 'same-origin',
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      },
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
    const state = this.#state;
    const controller = state.controller;
    if (controller) {
      controller.dispose();
      delete state.controller;
    }

    this.#layout.content.replaceChildren();
  }

  #displayAssets({
    container,
    assets,
    spinner = null,
    callback = null,
  } = {}) {
    if (!isHtmlObject(container) || !isObjectType(assets)) {
      console.warn('Failed to render Asset cards');
      return;
    }

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
          ref: key,
          name: details.verbose_name,
          desc: `Manage ${details.verbose_name_plural}`,
          icon: '&#xf1c0;',
          iconCls: 'as-icon--primary',
          action: 'Manage',
        },
        parent: container,
      });

      const button = card.querySelector('[data-role="action-btn"]');
      button.addEventListener('click', () => {
        if (typeof callback === 'function') {
          callback(key);
        }
      });
    }

    if (isRecordType(spinner) && typeof spinner.remove === 'function') {
      spinner.remove();
    }
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

    const url = this.#getTargetUrl('overview');
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
          const details = Const.CLU_ACTIVITY_CARDS.find(x => x.key === key);
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
        this.#displayAssets({
          assets: assets,
          container: quickAccessContent,
          spinner: spinners?.quickAccess ?? null,
          callback: (key) => {
            this.openPage('inventory', null, { type: key, labels: assets?.[key]?.details });
          }
        });
        spinners?.quickAccess?.remove?.();

        if (quickAccessContent.childElementCount < 1) {
          quickAccess.remove();
        }
      })
      .catch(console.error);
  }

  #renderModelView() {
    const state = this.#state;

    const type = state.page;
    const view = state.view ?? 'list';
    state.view = view;

    const label = transformTitleCase(state.page.replace('_', ' '));
    this.#clearContent();

    let article, container, header, createBtn;
    composeTemplate(this.#templates.base.model, {
      params: {
        id: type,
        title: `${transformTitleCase(view)} ${label}`,
        level: '1',
        content: '',
        headerCls: '',
        articleCls: 'dashboard-view__content--fill-w',
        sectionCls: view === 'list' ? 'dashboard-view__content-display' : 'dashboard-view__content-form',
      },
      parent: this.#layout.content,
      render: (elem) => {
        article = elem[0];

        header = article.querySelector('header');
        createBtn = header.querySelector('[data-role="create-btn"]');
        container = article.querySelector('section');
      }
    });

    let url;
    switch (view) {
      case 'list': {
        url = this.#getTargetUrl(type, { view: 'list' });
        header.classList.add('dashboard-view__content-header--constrain');

        const ctrl = new TableView({
          url: url,
          state: state,
          element: container,
          displayCallback: (_ref, trg) => {
            state.label = label;
            this.openPage(type, 'update', trg);
          }
        });
        state.controller = ctrl;

        createBtn.addEventListener('click', (e) => {
          this.openPage(type, 'create', null);
        });
      } break;

      case 'create': {
        url = this.#getTargetUrl(type, { view: 'create' });
        header.classList.add('dashboard-view__content-header--constrain-sm');
        createBtn.remove();

        const ctrl = new FormView({
          url: url,
          type: 'create',
          state: state,
          element: container,
          actionCallback: this.#actionCallback.bind(this),
        });
        state.controller = ctrl;

      } break;

      case 'update':
        url = this.#getTargetUrl(type, { view: 'update', kwargs: state.target });
        header.classList.add('dashboard-view__content-header--constrain-sm');
        createBtn.remove();

        const ctrl = new FormView({
          url: url,
          type: 'update',
          state: state,
          element: container,
          actionCallback: this.#actionCallback.bind(this),
        });
        state.controller = ctrl;

        break;

      default:
        break;
    }
  }

  #renderBrand() {
    const state = this.#state;
    const type = state.page;
    const view = 'update';
    state.view = view;
    state.target = null;

    const label = transformTitleCase(type.replace('_', ' '));
    this.#clearContent();

    let article, container, header, createBtn;
    composeTemplate(this.#templates.base.model, {
      params: {
        id: 'brand',
        title: `${transformTitleCase(view)} ${label}`,
        level: '1',
        content: '',
        headerCls: '',
        articleCls: 'dashboard-view__content--fill-w',
        sectionCls: view === 'list' ? 'dashboard-view__content-display' : 'dashboard-view__content-form',
      },
      parent: this.#layout.content,
      render: (elem) => {
        article = elem[0];

        header = article.querySelector('header');
        createBtn = header.querySelector('[data-role="create-btn"]');
        container = article.querySelector('section');
      }
    });

    const url = this.#getTargetUrl('brand', { view: 'update', kwargs: null });
    header.classList.add('dashboard-view__content-header--constrain-sm');
    createBtn.remove();

    const ctrl = new FormView({
      url: url,
      type: 'update',
      state: state,
      element: container,
    });
    state.controller = ctrl;
  }

  #renderInventory() {
    const state = this.#state;
    this.#clearContent();

    let view, url, target;
    view = state.view;
    target = state.target;
    if (!isRecordType(target)) {
      url = this.#getTargetUrl('inventory');

      let spinner;
      let spinnerTimeout = setTimeout(() => {
        spinner = startLoadingSpinner(activity, true);
      }, 200);

      const [assetList] = composeTemplate(this.#templates.base.group, {
        params: {
          id: 'asset-list',
          title: 'Inventory',
          level: '2',
          articleCls: 'dashboard-view__content--fill-w',
          sectionCls: 'dashboard-view__content-grid slim-scrollbar',
          content: '',
        },
        parent: this.#layout.content,
      });

      this.#fetch(url, { method: 'GET' })
        .then(res => {
          if (!spinner) {
            clearTimeout(spinnerTimeout);
          }

          return res.json();
        })
        .then(res => {
          const assets = res.assets;
          const content = assetList.querySelector('section');
          this.#displayAssets({
            assets: assets,
            container: content,
            spinner: spinner ?? null,
            callback: (key) => {
              this.openPage('inventory', null, { type: key, labels: assets?.[key]?.details });
            }
          });
          spinner?.remove?.();
  
          if (content.childElementCount < 1) {
            assetList.remove();
          }
        })
        .catch(console.error);
    } else {
      view = view ?? 'list';
      state.view = view;

      url = this.#getTargetUrl(target.type, { view: view, kwargs: target.kwargs });

      const type = target.type;
      const label = target?.labels?.verbose_name ?? transformTitleCase((target.type ?? 'Model').replace('_', ' '));;

      let article, container, header, createBtn;
      composeTemplate(this.#templates.base.model, {
        params: {
          id: type,
          title: `${transformTitleCase(view)} ${label}`,
          level: '1',
          content: '',
          headerCls: '',
          articleCls: 'dashboard-view__content--fill-w',
          sectionCls: view === 'list' ? 'dashboard-view__content-display' : 'dashboard-view__content-form',
        },
        parent: this.#layout.content,
        render: (elem) => {
          article = elem[0];
  
          header = article.querySelector('header');
          createBtn = header.querySelector('[data-role="create-btn"]');
          container = article.querySelector('section');
        }
      });
  
      switch (view) {
        case 'list': {
          header.classList.add('dashboard-view__content-header--constrain');
  
          const ctrl = new TableView({
            url: url,
            state: state,
            element: container,
            displayCallback: (_ref, trg) => {
              this.openPage('inventory', 'update', { type: type, labels: target?.labels, kwargs: trg });
            }
          });
          state.controller = ctrl;

          createBtn.addEventListener('click', (e) => {
            this.openPage('inventory', 'create', { type: type, labels: target?.labels });
          });
        } break;
  
        case 'create': {
          header.classList.add('dashboard-view__content-header--constrain-sm');
          createBtn.remove();
  
          const ctrl = new FormView({
            url: url,
            type: 'create',
            state: state,
            element: container,
            actionCallback: this.#actionCallback.bind(this),
          });
          state.controller = ctrl;
  
        } break;
  
        case 'update':
          header.classList.add('dashboard-view__content-header--constrain-sm');
          createBtn.remove();
  
          const ctrl = new FormView({
            url: url,
            type: 'update',
            state: state,
            element: container,
            actionCallback: this.#actionCallback.bind(this),
          });
          state.controller = ctrl;
  
          break;
  
        default:
          break;
      }
    }
  }


  /*************************************
   *                                   *
   *              Events               *
   *                                   *
   *************************************/
  #eventHandler(e) {

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

  #actionCallback(action, e, props, _formView, _btn) {
    e.preventDefault();

    const { type, url } = props;
    if (type !== 'update' || !stringHasChars(url)) {
      return;
    }

    switch (action) {
      case 'reset_pwd': {
        ModalFactory.create({
          title: 'Are you sure?',
          content: 'This will immediately send a password reset e-mail to the user.',
          beforeAccept: () => {
            return this.#fetch(url, { method: 'PUT', headers: { 'X-Target': action } })
              .then(result => {
                if (!result.ok) {
                  throw new Error('[ErrStatus] Failed to send reset e-mail.')
                }

                return result.json();
              });
          }
        })
          .then(async result => {
            await result.data; // SINK

            window.ToastFactory.push({
              type: 'success',
              message: 'Password reset e-mail successfully sent.',
              duration: 4000,
            });
          })
          .catch((e) => {
            if (!(e instanceof ModalFactory.ModalResults)) {
              if (typeof onError === 'function') {
                return onError();
              }

              window.ToastFactory.push({
                type: 'error',
                message: 'Failed to send reset e-mail.',
                duration: 4000,
              });
              return console.error(e);
            }

            if (e.name === ModalFactory.ButtonTypes.REJECT) {

            }
          });
      } break;

      default:
        break;
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
      throw new Error('InitError: Failed to resolve DashboardService element');
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
