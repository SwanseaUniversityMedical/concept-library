const GT_CONSENT_DEFAULT = {
  ad_storage: 'denied',
  ad_user_data: 'denied',
  security_storage: 'denied',
  analytics_storage: 'granted',
  ad_personalization: 'denied',
  functionality_storage: 'granted', 
  personalization_storage: 'denied',
  wait_for_update: 500,
};

const buildAnalyticsConsent = (value, forceFunctional = false) => {
  return {
    ad_storage: value,
    ad_user_data: value,
    security_storage: value,
    analytics_storage: !forceFunctional ? 'granted' : value,
    ad_personalization: value,
    functionality_storage: !forceFunctional ? 'granted' : value, 
    personalization_storage: value,
  };
}

const hasAnalyticsConsent = (type, ageInDays = 365) => {
  type = typeof type === 'string'
    ? type.toLowerCase()
    : type;

  switch (type) {
    case 'essential':
    case 'analytics': {
      const consent = localStorage.getItem('cookie_consent');
      if (consent !== type) {
        break;
      }

      let date = localStorage.getItem('cookie_consent_date');
      try {
        date = !isStringEmpty(date)
          ? new Date(date)
          : null;
      }
      catch {
        date = null;
      }

      if (isNullOrUndefined(date) || !(date instanceof Date)) {
        break;
      }

      const now = new Date();
      const dif = Math.round((now - date) / (1000 * 60 * 60 * 24));
      if (dif <= ageInDays) {
        return true;
      }
    } break;

    case 'any':
      const consentedEssential = hasAnalyticsConsent('essential');
      const consentedAnalytics = hasAnalyticsConsent('analytics');
      return consentedEssential || consentedAnalytics;

    default:
      break;
  }

  return false
}

const setAnalyticsCookie = (type) => {
  localStorage.setItem('cookie_consent', type);
  localStorage.setItem('cookie_consent_date', new Date().toISOString());
}

const loadTagManager = (id) => {
  const script = document.createElement('script');
  script.src = `https://www.googletagmanager.com/gtag/js?id=${id}`;
  return document.head.appendChild(script);
}

const asyncLoadTagManager = async (config) => new Promise((resolve, reject) => {
  const { configId, uid } = config;

  const script = document.createElement('script');
  script.src = `https://www.googletagmanager.com/gtag/js?id=${configId}`;
  script.async = true;
  script.onload = () => {    
    window.dataLayer = window.dataLayer || [];

    function gtag() {
      window.dataLayer.push(arguments);
    }
    window.gtag = gtag;

    const cfg = {
      cookie_flags: 'max-age=31536000;secure;samesite=none',
      cookie_domain: 'none',
    };

    if (typeof uid === 'number' && Number.isSafeInteger(uid)) {
      cfg.user_id = uid;
    }

    window.gtag('js', new Date())
    window.gtag('config', configId, cfg);

    resolve(script);
  };
  script.onerror = (e) => reject(new Error('Script load error', { cause: e }));
  document.head.append(script);
});

const disposeTagManager = () => {
  const scripts = Array.from(document.querySelectorAll('script[src*="googletagmanager.com"]'));
  scripts.forEach(gaScript => {
    gaScript.remove();
  });
};

const setAnalyticsEnv = (consent = null, target = 'update') => {
  if (stringHasChars(consent)) {
    window.gtag('consent', target, buildAnalyticsConsent(consent));
  } else {
    window.gtag('consent', 'default', GT_CONSENT_DEFAULT);
  }
}

onEnterDomState('loading')
  .then(() => {
    const cookieSrc = document.querySelector('script[data-src="cookies"]');
    if (!cookieSrc) {
      return;
    }

    const cookieTarget = getAnalyticsTarget();
    for (let key in cookieSrc.dataset) {
      let value = cookieSrc.dataset[key]
      switch (key) {
        case 'src':
          continue;

        case 'uid':
          const parsed = tryParseNumber(value)
          value = parsed.type === 'int' ? parsed.value : null;
          break;

        default:
          break;
      }

      cookieTarget[key] = value;
    }

    return asyncLoadTagManager(cookieTarget)
      .then((script) => {
        return { cookieTarget, script };
      })
  })
  .then(async (res) => {
    return domReady.then(() => res)
  })
  .then(({ cookieTarget, script }) => {
    const cookieCard = document.querySelector('.cookie_card');
    const cookieAlert = document.querySelector('.cookiealert');
    if (!cookieCard || !cookieAlert) {
      return;
    }

    const toggleCookieVisibility = (val) => {
      if (val) {
        cookieCard.classList.remove('show');
        cookieAlert.classList.add('show');
        return;
      }

      cookieCard.classList.add('show');
      cookieAlert.classList.remove('show');
    }

    const hasInit = hasAnalyticsConsent('any');
    toggleCookieVisibility(!hasInit)

    // Load gtag if consent is known
    setAnalyticsEnv(
      hasInit
        ? hasAnalyticsConsent('analytics') ? 'granted' : 'denied'
        : null
      ,
      'default'
    );

    // Accept-Reject overlay
    const acceptCookie = document.querySelector('.acceptcookies');
    acceptCookie?.addEventListener?.('click', () => {
      if (!hasAnalyticsConsent('analytics')) {
        setAnalyticsEnv('granted');
      }

      setAnalyticsCookie('analytics');
      toggleCookieVisibility(false);
    });

    const rejectCookie = document.querySelector('.rejectcookies');
    rejectCookie?.addEventListener?.('click', () => {
      if (hasAnalyticsConsent('analytics')) {
        setAnalyticsEnv('denied');
      }

      setAnalyticsCookie('essential');
      toggleCookieVisibility(false);
    });

    // Toggle post-consent window / customisation modal
    const preferenceCookies = document.querySelectorAll('.preferencecookies');
    for (let i = 0; i < preferenceCookies.length; ++i) {
      const btn = preferenceCookies.item(i);
      btn.addEventListener('click', () => {
        ModalFactory.create({
          id: 'cookie-dialog',
          title: 'Privacy Settings',
          content: `
            <p>
              We use cookies and similar technologies that are necessary to operate the website. Additional cookies
              are only used with your consent.
            <p>
            </p>
              We use the additional cookies to perform analyses of website usage and to check marketing measures for their efficiency.
              These analyses are carried out to provide you with a better user experience on this website.
            <p>
              Please note that you are free to give, deny, or withdraw your consent at any time by using the <em>"cookie settings"</em> link at the bottom of each page.
              Otherwise, you can consent to our use of cookies by clicking <em>"Save selection"</em>.
            </p>
            <p>
              For more information about what information is collected and how it is shared with our partners, please read our <a href="${cookieTarget.privacyurl}" target=_blank rel="noopener">Privacy and cookie policy</a>.
            </p>
            <div class="checkbox-item-container min-size">
              <input id="neccesary-cookies" type="checkbox" disabled checked class="checkbox-input" data-value="1" data-name="must-cookies"/>
              <label for="neccesary-cookies">Necessary cookies (functional cookies and EU & UK GDPR-compliant analytics)</label>
            </div>
            <div class="checkbox-item-container min-size">
              <input id="stats-check" type="checkbox" class="checkbox-input" data-value="0" data-name="analytics"/>
              <label for="stats-check">Google ad tracking, personalisation & security</label.
            </div>
            <p>Monitoring website usage and optimizing the user experience via Google Analytics.</p>
          `,
          buttons: [
            {
              name: 'Cancel',
              type: ModalFactory.ButtonTypes.REJECT,
              html: `<button class="secondary-btn text-accent-darkest bold washed-accent" id="cancel-button"></button>`,
            },
            {
              name: 'Save selection',
              type: ModalFactory.ButtonTypes.CONFIRM,
              html: `<button class="primary-btn text-accent-darkest bold secondary-accent" id="save-button"></button>`,
            },
          ],
          beforeAccept: (modal) => {
            const checkbox = modal.querySelector('#stats-check');
            return { analyticsConsent: checkbox?.checked ?? false };
          },
          onRender: (modal) => {
            const checkbox = modal.querySelector('#stats-check');
            if (checkbox) {
              checkbox.checked = hasAnalyticsConsent('any')
                ? hasAnalyticsConsent('analytics')
                : true;
            }
          }
        })
          .then(res => {
            const hasAnalytics = hasAnalyticsConsent('analytics');
            if (res?.data?.analyticsConsent) {
              if (hasAnalytics) {
                return;
              }

              setAnalyticsEnv('granted');

              setAnalyticsCookie('analytics');
              toggleCookieVisibility(false);
              return;
            }

            if (hasAnalytics) {
              setAnalyticsEnv('denied');
            }

            setAnalyticsCookie('essential');
            toggleCookieVisibility(false);
          })
          .catch(res => {
            if (!!res && !(res instanceof ModalFactory.ModalResults)) {
              return console.error(res);
            }
          })
      });
    }

    document.documentElement.addEventListener(
      'click',
      (e) => {
        e = e || window.event;

        const trg = e.target || e.srcElement;
        if (isNullOrUndefined(trg) || !trg.matches('a[href][data-ba-hook="interaction"]')) {
          return true;
        }

        let attributes;
        if (!trg.attributes.hasOwnProperty('data-ba-resource')) {
          const obj = tryGetRootElement(trg, '*[data-ba-resource]:not([data-ba-hook])');
          if (isNullOrUndefined(obj)) {
            return true;
          }

          attributes = [...trg.attributes];
          attributes = attributes.concat(
            [...obj.attributes].filter(
              x1 => !attributes.some(x0 => x0.name === x1.name)
            )
          );
        } else {
          attributes = trg.attributes;
        }

        const dataset = { };
        for (let i = 0; i < attributes.length; ++i) {
          const { name, value } = attributes[i];
          if (!name.startsWith('data-ba-')) {
            continue;
          }

          dataset[name.replace('data-ba-', '')] = decodeURIComponent(value);
        }

        const href = trg.getAttribute('href');
        tryAnalytics((manager) => {
          manager('event', 'interaction', {
            ix_value: href,
            ix_brand: cookieTarget.brand !== 'none' ? cookieTarget.brand : null,
            ix_source: dataset.source,
            ix_origin: stringHasChars(dataset.origin) ? dataset.origin : null,
            ix_resource: dataset.resource,
          });
        })
          .catch(() => { /* SINK */ })

        return true;
      },
      {
        capture: true,
        passive: false,
      }
    );
  });
