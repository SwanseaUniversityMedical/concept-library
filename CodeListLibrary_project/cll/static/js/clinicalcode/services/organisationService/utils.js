export const confirmationPrompt = ({ 
  title, 
  content,
  onAccept,
  onRender=null,
  beforeAccept=null,
  onReject=null,
  onError=null
}) => {
  return ModalFactory.create({
    title: title,
    content: content,
    onRender: onRender,
    beforeAccept: beforeAccept
  })
    .then((result) => onAccept(result))
    .catch((e) => {
      if (!!e && !(e instanceof ModalFactory.ModalResults)) {
        if (typeof onError === 'function') {
          return onError();
        }

        return console.error(e);
      }
  
      if (e.name === ModalFactory.ButtonTypes.REJECT) {
        if (typeof onReject === 'function') {
          return onReject();
        }
      }
    });
}

export const getStatsIcon = (key) => {
  switch (key) {
    case 'total':
      return {
        title: 'Content',
        icon: '&#xe473;',
        desc: 'No. of owned Phenotypes',
      }
    case 'created':
      return {
        title: 'Created',
        icon: '&#xf234;',
        desc: 'No. created in the last 30 days',
      }
    case 'edited':
      return {
        title: 'Edited',
        icon: '&#xf4ff;',
        desc: 'No. edited in the last 30 days',
      }
    case 'views':
      return {
        title: 'Phenotypes',
        icon: '&#xf06e;',
        desc: 'View count in the last 30 days',
      }
    case 'downloads':
      return {
        title: 'Downloads',
        icon: '&#xf0ed;',
        desc: 'Downloads in the last 30 days',
      }
    case 'popular':
      return {
        title: 'Popular',
        icon: '&#xf06d;',
        desc: 'Top 5 Phenotypes',
      }
    default:
      // '&#xf56c';
      return null;
  }
}

export const composeStatsCard = (parent, key, data, entityResolver) => {
  if (typeof data === 'undefined' || data === null) {
    console.warn(`Failed to compose StatsCard<keyof "${key}"> w/ err:\nInvalid data`);
    return null;
  }

  const info = getStatsIcon(key);
  if (typeof info === 'undefined' || info === null) {
    console.warn(`Failed to compose StatsCard<keyof "${key}"> w/ err:\nUnknown key type`);
    return null;
  }

  let template;
  let className = getObjectClassName(data);
  switch (className) {
    case 'Number':
      template = '<article class="org-stats-card"> \
        <header class="org-stats-card__header"> \
          <h3>${title}</h3> \
          <span data-icon="${icon}" aria-hidden="true" class="as-icon as-icon--warning"></span> \
        </header> \
        <p class="org-stats-card__desc">${desc}</p> \
        <figure class="org-stats-card__data">${data}</figure> \
      </article>'
      break;

    case 'Array':
      data = Object.values(data)
      if (data.length < 1) {
        return null;
      }

      data = data
        .reduce((out, x) => {
          const url = entityResolver(x.id);
          out.push(`<div class="org-stats-card__items-elem">
            <a href="${url}">${x.id}</a>
            <span>${x.view_count}</span>
          </div>`)

          return out;
        }, [])
        .join('\n')

      template = '<article class="org-stats-card"> \
        <header class="org-stats-card__header"> \
          <h3>${title}</h3> \
          <span data-icon="${icon}" aria-hidden="true" class="as-icon as-icon--warning"></span> \
        </header> \
        <p class="org-stats-card__desc">${desc}</p> \
        <figure class="org-stats-card__items slim-scrollbar"> \
          ${data} \
        </figure> \
      </article>'

      break;

    default:
      console.warn(`Failed to compose StatsCard<keyof "${key}"> w/ err:\nUnknown datatype for case Data<class: ${className}>`)
      return null;
  }

  return composeTemplate(template, {
    params: Object.assign(info, { 'data': data }),
    parent: parent,
  });
}