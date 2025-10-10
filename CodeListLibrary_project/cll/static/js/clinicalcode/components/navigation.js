import FuzzyQuery from './fuzzyQuery.js';

/**
  * updateNavBarStyle
  * @desc Updates the navigation bar style from transparent to opaque dependent on whether the user has scrolled down the page
  * @param {node} navbar The navigation bar element
  * 
  */
const updateNavBarStyle = (navbar) => {
  const y = window.scrollY;

  if (window.innerWidth <= 768){
    navbar.classList.remove('transparent')
    return;
  }

  if (y >= navbar.offsetHeight*0.25) {
    navbar.classList.add('scrolled');
    navbar.classList.remove('transparent');
  } else {
    navbar.classList.remove('scrolled');
    navbar.classList.add('transparent');
  }
}

/**
  * computeBurgerProperty
  * @desc Computes the --as-burger CSS property, see SCSS for further information
  * @param {node} burger The hamburger element
  * @returns {boolean} The value of the computed property
  * 
  */
const computeBurgerProperty = (burger) => {
  const value = window.getComputedStyle(burger, ':after').getPropertyValue('--as-burger').replace(/[^\w!?]/g, '');
  return /^\s*(true|1|on)\s*$/i.test(value);
}

/**
  * initHamburgerMenu
  * @desc Initialises the hamburger menu for mobiles on the navigation bar
  * 
  */
const initHamburgerMenu = () => {
  const nav = document.querySelector('.page-navigation');
  const burger = document.querySelector('.page-navigation__buttons');
  const panel = document.querySelector('.page-navigation__items');
  const overlay = document.querySelector('.page-navigation__overlay');
  const avatarMenu = document.querySelector('#dropdown-account');
  const submenu = document.querySelector('.nav-dropdown__content');
  const nestedMenu = document.querySelector('.nested-menu');

  const closeItems = () => {
    panel?.classList?.remove?.('open');
    submenu?.classList?.remove?.('open');
    avatarMenu?.classList?.remove?.('open');
    nestedMenu?.classList?.remove?.('open');
    overlay.style.display = 'none';
  }

  burger.addEventListener('click', e => {
    if (panel?.classList?.contains?.('open')) {
      closeItems();
      return;
    }

    const isBurger = computeBurgerProperty(burger);
    if (isBurger) {
      panel.classList.add('open');
      overlay.style.display = 'block';
      return;
    }
  });

  document.addEventListener('click', e => {
    const element = e.target;
    if (burger.contains(element) || panel.contains(element)) {
      return;
    }

    closeItems();
  })

  let isInMobileView = computeBurgerProperty(burger);
  const resizeObserver = new ResizeObserver(() => {
    const newValue = computeBurgerProperty(burger);
    if (isInMobileView && !newValue) {
      closeItems();

      const focusedItem = document.activeElement;
      if (isHtmlObject(focusedItem) && nav.contains(focusedItem)) {
        focusedItem.blur();
      }
    }
    isInMobileView = newValue;
  });
  resizeObserver.observe(burger);
}

/**
 * submenuMobile
 * @desc ...?
 * 
 */
const submenuMobile = () => {
  const burger = document.querySelector('.page-navigation__buttons');

  const aboutText = document.querySelector('.nav-dropdown__text#About');
  const aboutMenu = aboutText?.parentElement?.querySelector?.('.nav-dropdown__content');

  const avatarText = document.querySelector('.avatar-content');
  const avatarMenu = avatarText?.parentElement?.querySelector?.('.nav-dropdown__content');

  const menus = {
    about  : { valid:  aboutText &&  aboutMenu, btn:  aboutText, smu:  aboutMenu },
    avatar : { valid: avatarText && avatarMenu, btn: avatarText, smu: avatarMenu },
  }

  // Hnd submenu visibility
  const toggleSubmenu = (trg) => {
    const elems = stringHasChars(trg)
      ? menus[trg]
      : null;

    if (!isObjectType(elems) || !elems.valid) {
      return;
    }

    const { btn, smu } = elems;
    if (smu.classList.contains('open')) {
      btn.classList.remove('open');
      smu.classList.remove('open');
      return;
    }

    let objs;
    for (const key in menus) {
      objs = menus[key];
      if (key === trg || !objs.valid) {
        continue;
      }

      objs.btn.classList.remove('open');
      objs.smu.classList.remove('open');
    }

    btn.classList.add('open');
    smu.classList.add('open');
  };

  const submenuHnd = (e) => {
    if (!computeBurgerProperty(burger)) {
      return true;
    }

    const elem = e.target;
    if (!isHtmlObject(elem)) {
      return true;
    }

    let trg;
    if (aboutText === elem || aboutText.contains(elem)) {
      trg = 'about';
    } else if (avatarText === elem || avatarText.contains(elem)) {
      trg = 'avatar';
    }

    if (isNullOrUndefined(trg)) {
      return;
    }

    e.preventDefault();
    toggleSubmenu(trg);
  };

  aboutText?.addEventListener?.('click', submenuHnd, { capture: true, passive: false });
  avatarText?.addEventListener?.('click', submenuHnd, { capture: true, passive: false });

  // Hnd nested visibility
  const nestedContainer = document.querySelector('.content-container__nested > a');
  const nestedMenu = nestedContainer?.parentElement?.querySelector?.('.nested-menu');
  nestedContainer?.addEventListener?.('click', (e) => {
    if (!computeBurgerProperty(burger) || isNullOrUndefined(nestedMenu)) {
      return true;
    }

    e.preventDefault();

    const method = nestedMenu.classList.contains('open')
      ? nestedMenu.classList.remove
      : nestedMenu.classList.add;

    method?.call?.(nestedMenu.classList, 'open');
  });
}

/**
 * searchBar
 * @desc ...?
 * 
 */
const searchBar = () => {
  const searchIcon = document.querySelector('.search-navigation__search-icon');
  const searchInput = document.querySelector('.search-navigation__search-input');
  searchIcon.addEventListener('mouseover', (e) => {
    searchInput.focus();
  });

  document.addEventListener('mouseout', (e) => {
    if (searchInput.contains(e.target) || searchIcon.contains(e.target)) {
      return;
    }

    searchInput.blur();
  });
}

/**
  * setNavigation
  * @desc Sets the navigation bar's buttons to active or inactive dependent on the URL of the page
  * @param {node} navbar The navigation bar element
  */
const setNavigation = (navbar) => {
  const links = navbar.querySelectorAll('.page-navigation__items a');

  let path = getCurrentPath();
  path = path.toLocaleLowerCase();

  let currentBrand = document.documentElement.getAttribute('data-brand');
  if (!isNullOrUndefined(currentBrand)) {
    currentBrand = currentBrand.toLocaleLowerCase();
    path = path.replace(`${currentBrand}\/`, '');
  }
  
  let root = path.match(/^\/(\w+)/);
  root = !isNullOrUndefined(root) ? root[1] : null;

  let distance, closest;
  for (let i = 0; i < links.length; ++i) {
    const link = links[i];

    // match by data-root attribute
    let roots = link.getAttribute('data-root');
    if (root && !isNullOrUndefined(roots)) {
      roots = roots.split(',');
      if (roots.includes(root)) {
        closest = link;
        break;
      }
    }

    // match by link
    let href = link.getAttribute('href');
    if (!stringHasChars(href)) {
      continue;
    }

    href = href.replace(/\/$/, '').toLocaleLowerCase();

    const dist = FuzzyQuery.Distance(path, href);
    if (typeof closest === 'undefined' || dist < distance) {
      distance = dist;
      closest = link;
    }
  }

  if (typeof closest !== 'undefined') {
    closest.classList.add('active');
  }
}

const manageBrandTargets = () => {
  const elements = [...document.querySelectorAll('.userBrand')];
  const brandSource = document.querySelector('script[type="application/json"][name="brand-targets"]');
  if (elements.length < 1 || isNullOrUndefined(brandSource)) {
    return;
  }

  const path = window.location.pathname.slice(1);
  const oldRoot = path.split('/')[0];
  const brandTargets = JSON.parse(brandSource.innerText.trim());

  let isProductionRoot = brandSource.getAttribute('host-target');
  if (isNullOrUndefined(isProductionRoot)) {
    isProductionRoot = false;
  } else if (typeof isProductionRoot === 'string') {
    isProductionRoot = ['true', '1'].indexOf(isProductionRoot.toLowerCase()) >= 0;
  }

  const tryGetBrandNavMap = (ref) => {
    const map = isHtmlObject(ref)
      ? ref.querySelector('script[type="application/json"][name="brand-mapping"]')
      : null;

    let parsed = null;
    if (!isNullOrUndefined(map)) {
      try {
        parsed = JSON.parse(map.innerText);
      }
      catch { }

      if (!isNullOrUndefined(parsed) && !isObjectType(parsed)) {
        parsed = null;
      }
    }

    return parsed;
  }

  const handleBrandTarget = (e) => {
    let current = getCurrentBrandPrefix();
    if (current.startsWith('/')) {
      current = current.substring(1);
    }
    current = current.toUpperCase();

    const trg = e.target;
    const ref = elements.find(x => (stringHasChars(x.getAttribute('value')) ? x.getAttribute('value').toUpperCase() : '') === current);

    const m0 = tryGetBrandNavMap(ref);
    const m1 = tryGetBrandNavMap(trg);
    if (!isNullOrUndefined(m0) && !isNullOrUndefined(m1)) {
      const pathIndex = brandTargets.indexOf(oldRoot.toUpperCase()) == -1 ? 0 : 1;
      const pathTarget = path.split('/').slice(pathIndex);
      const pathRoot = pathTarget?.[0];
      if (stringHasChars(pathRoot)) {
        let uRes = Object.entries(m0).find(([k, v]) => k.endsWith('_url') && v === pathRoot);
        uRes = (Array.isArray(uRes) && uRes.length >= 2)
          ? m1?.[uRes[0]]
          : null;

        if (stringHasChars(uRes) && uRes !== pathRoot) {
          pathTarget[0] = uRes;

          uRes = (
            pathIndex
              ? [oldRoot, ...pathTarget]
              : pathTarget
          )
            .join('/');

          navigateBrandTargetURL(brandTargets, isProductionRoot, trg, oldRoot, uRes);
          return;
        }
      }
    }

    navigateBrandTargetURL(brandTargets, isProductionRoot, trg, oldRoot, path);
  };

  for (const element of elements) {
    element.addEventListener('click', handleBrandTarget);
  }
}

/**
 * Main thread
 * @desc initialises the component once the dom is ready
 * 
 */
domReady.finally(() => {
  const navbar = document.querySelector('.page-navigation');
  updateNavBarStyle(navbar);
  submenuMobile();
  searchBar();

  document.addEventListener('scroll', e => {
    updateNavBarStyle(navbar);
  });

  initHamburgerMenu();
  setNavigation(navbar);

  manageBrandTargets();
});
