import * as orgUtils from './utils.js';

class Autocomplete {
  constructor({
    rootNode,
    inputNode,
    resultsNode,
    searchFn,
    shouldAutoSelect = false,
    onShow = () => {},
    onHide = () => {}
  } = {}) {
    this.rootNode = rootNode
    this.inputNode = inputNode
    this.resultsNode = resultsNode
    this.searchFn = searchFn
    this.shouldAutoSelect = shouldAutoSelect
    this.onShow = onShow
    this.onHide = onHide
    this.activeIndex = -1
    this.resultsCount = 0
    this.showResults = false
    this.hasInlineAutocomplete = this.inputNode.getAttribute('aria-autocomplete') === 'both'

    // Setup events
    document.body.addEventListener('click', this.handleDocumentClick)
    this.inputNode.addEventListener('keyup', this.handleKeyup)
    this.inputNode.addEventListener('keydown', this.handleKeydown)
    this.inputNode.addEventListener('focus', this.handleFocus)
    this.resultsNode.addEventListener('click', this.handleResultClick)
  }
  
  handleDocumentClick = event => {
    if (event.target === this.inputNode || this.rootNode.contains(event.target)) {
      return
    }
    this.hideResults()
  }

  handleKeyup = event => {
    const { key } = event

    switch (key) {
      case 'ArrowUp':
      case 'ArrowDown':
      case 'Escape':
      case 'Enter':
        event.preventDefault()
        return
      default:
        this.updateResults()
    }
    
    if (this.hasInlineAutocomplete) {
      switch(key) {
        case 'Backspace':
          return
        default:
          this.autocompleteItem()
      }
    }
  }
  
  handleKeydown = event => {
    const { key } = event
    let activeIndex = this.activeIndex
    
    if (key === 'Escape') {
      this.hideResults()
      this.inputNode.value = ''
      return
    }
    
    if (this.resultsCount < 1) {
      if (this.hasInlineAutocomplete && (key === 'ArrowDown' || key === 'ArrowUp')) {
        this.updateResults()
      } else {
        return
      }
    }
    
    const prevActive = this.getItemAt(activeIndex)
    let activeItem
    
    switch(key) {
      case 'ArrowUp':
        if (activeIndex <= 0) {
          activeIndex = this.resultsCount - 1
        } else {
          activeIndex -= 1
        }
        break
      case 'ArrowDown':
        if (activeIndex === -1 || activeIndex >= this.resultsCount - 1) {
          activeIndex = 0
        } else {
          activeIndex += 1
        }
        break
      case 'Enter':
        activeItem = this.getItemAt(activeIndex)
        this.selectItem(activeItem)
        return
      case 'Tab':
        this.checkSelection()
        this.hideResults()
        return
      default:
        return
    }
    
    event.preventDefault()
    activeItem = this.getItemAt(activeIndex)
    this.activeIndex = activeIndex
    
    if (prevActive) {
      prevActive.classList.remove('selected')
      prevActive.setAttribute('aria-selected', 'false')
    }
    
    if (activeItem) {
      this.inputNode.setAttribute('aria-activedescendant', `autocomplete-result-${activeIndex}`)
      activeItem.classList.add('selected')
      activeItem.setAttribute('aria-selected', 'true')
      if (this.hasInlineAutocomplete) {
        this.inputNode.value = activeItem.innerText
      }
    } else {
      this.inputNode.setAttribute('aria-activedescendant', '')
    }
  }
  
  handleFocus = event => {
    this.updateResults()
  }
  
  handleResultClick = event => {
    if (event.target && event.target.nodeName === 'LI') {
      this.selectItem(event.target)
    }
  }
  
  getItemAt = index => {
    return this.resultsNode.querySelector(`#autocomplete-result-${index}`)
  }
  
  selectItem = node => {
    if (node) {
      this.inputNode.value = node.innerText
      this.hideResults()
    }
  }
  
  checkSelection = () => {
    if (this.activeIndex < 0) {
      return
    }
    const activeItem = this.getItemAt(this.activeIndex)
    this.selectItem(activeItem)
  }
  
  autocompleteItem = event => {
    const autocompletedItem = this.resultsNode.querySelector('.selected')
    const input = this.inputNode.value
    if (!autocompletedItem || !input) {
      return
    }
    
    const autocomplete = autocompletedItem.innerText
    if (input !== autocomplete) {
      this.inputNode.value = autocomplete
      this.inputNode.setSelectionRange(input.length, autocomplete.length)
    }
  }
  
  updateResults = () => {
    const input = this.inputNode.value
    const results = this.searchFn(input)
    
    this.hideResults()
    if (results.length === 0) {
      return
    }
    
    this.resultsNode.innerHTML = results.map((result, index) => {
      const isSelected = this.shouldAutoSelect && index === 0
      if (isSelected) {
        this.activeIndex = 0
      }
      return `
        <li
          id='autocomplete-result-${index}'
          class='autocomplete-result${isSelected ? ' selected' : ''}'
          role='option'
          ${isSelected ? "aria-selected='true'" : ''}
        >
          ${result}
        </li>
      `
    }).join('')
    
    this.resultsNode.classList.remove('hidden')
    this.rootNode.setAttribute('aria-expanded', true)
    this.resultsCount = results.length
    this.shown = true
    this.onShow()
  }
  
  hideResults = () => {
    this.shown = false
    this.activeIndex = -1
    this.resultsNode.innerHTML = ''
    this.resultsNode.classList.add('hidden')
    this.rootNode.setAttribute('aria-expanded', 'false')
    this.resultsCount = 0
    this.inputNode.setAttribute('aria-activedescendant', '')
    this.onHide()
  }
}

const renderMembersList = (root, token, data) => {
  if (isNullOrUndefined(data)) {
    return fetch(getCurrentURL(), {
      method: 'GET',
      cache: 'no-cache',
      credentials: 'same-origin',
      withCredentials: true,
      headers: {
        'X-Target': 'get_reloaded_data',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': token,
        'Authorization': `Bearer ${token}`
      }
    })
      .then(response => response.json())
      .then(response => renderMembersList(root, token, response.members))
  }

  const memberList = root.querySelector('#member-role-list');
  while (memberList.firstChild) {
    memberList.removeChild(memberList.firstChild);
  }

  const memberMessage = root.querySelector('#no-members')
  if (isNullOrUndefined(data) || data.length < 1) {
    memberMessage.classList.add('show');
  } else {
    memberMessage.classList.remove('show');
  }
  
  const templates = { };
  root.querySelectorAll('[data-owner="management"]').forEach((v, k) => {
    const name = v.getAttribute('data-name');
    templates[name] = v.innerHTML;
  });

  for (let i = 0; i < data.length; i++) {
    const obj = data[i];
    const [card] = composeTemplate(templates.member, {
      params: {
        userid: obj.user_id,
        name: obj.username,
      },
      modify: [{
        select: 'span',
        parent: memberList,
        apply: (elem) => { 
          const spn = elem.querySelector('.action-buttons');

          let [btn] = composeTemplate(templates.dropdown, {
            params: {
              uid: obj.user_id,
            },
          });
          btn = spn.appendChild(btn);

          btn.addEventListener('change', (e) => {
            const selected = btn.options[btn.selectedIndex];
            const targetValue = parseInt(selected.value);

            if (targetValue !== obj.role && !isNaN(targetValue)) {
              const prevValue = obj.role;

              fetch(getCurrentURL(), {
                method: 'POST',
                cache: 'no-cache',
                credentials: 'same-origin',
                withCredentials: true,
                headers: {
                  'X-Target': 'change_user_role',
                  'X-Requested-With': 'XMLHttpRequest',
                  'X-CSRFToken': token,
                  'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                  uid: obj.user_id,
                  oid: obj.organisation_id,
                  rid: targetValue
                })
              })
                .then(response => response.json())
                .then(() => {
                  if (parseInt(selected.value) !== prevValue) {
                    obj.role = targetValue;
                  }
                })
                .catch((err) => {
                  btn.value = prevValue;
                  obj.role = prevValue;
                });
            }
          });

          const opt = btn.querySelector(`[value="${obj.role}"]`);
          if (opt) {
            opt.selected = true;
          }
        },
      }]
    });
    
    const delete_btn = card.querySelector(`[data-target="delete"]`);
    delete_btn.addEventListener('click', (e) => {
      orgUtils.confirmationPrompt({
        title: 'Are you sure?',
        content: '<p>This will remove the user from the organisation</p>',
        onAccept: () => {
          return fetch(getCurrentURL(), {
            method: 'POST',
            cache: 'no-cache',
            credentials: 'same-origin',
            withCredentials: true,
            headers: {
              'X-Target': 'delete_member',
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': token,
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              uid: obj.user_id,
              oid: obj.organisation_id
            })
          })
            .then(response => response.json())
            .then(response => renderMembersList(root, token, null))
        }
      });
    });
  }
}

const renderInvitesList = (root, token, data) => {
  if (isNullOrUndefined(data)) {
    return fetch(getCurrentURL(), {
      method: 'GET',
      cache: 'no-cache',
      credentials: 'same-origin',
      withCredentials: true,
      headers: {
        'X-Target': 'get_reloaded_data',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': token,
        'Authorization': `Bearer ${token}`
      }
    })
      .then(response => response.json())
      .then(response => {
        return renderInvitesList(root, token, response.invites);
      })
  }

  const user_list = data.users;
  const active_invites = data.active;

  const invitesList = root.querySelector('#invite-list-container');
  while (invitesList.firstChild) {
    invitesList.removeChild(invitesList.firstChild);
  }

  const inviteMessage = root.querySelector('#no-invites')
  if (isNullOrUndefined(active_invites) || active_invites.length < 1) {
    inviteMessage.classList.add('show');
  } else {
    inviteMessage.classList.remove('show');
  }

  const templates = { };
  root.querySelectorAll('[data-owner="invite"]').forEach((v, k) => {
    const name = v.getAttribute('data-name');
    templates[name] = v.innerHTML;
  });

  const autocomplete = new Autocomplete({
    rootNode: document.querySelector('.autocomplete-container'),
    inputNode: document.querySelector('.autocomplete-input'),
    resultsNode: document.querySelector('.autocomplete-results'),
    searchFn: (input) => {
      if (input.length <= 3) {
        return []
      }

      return user_list.filter(
        item => item.username.toLowerCase().startsWith(input.toLowerCase())
      ).map(
        item => item.username
      );
    },
    shouldAutoSelect: true
  });

  document.querySelector('#invite-btn').addEventListener('click', (e) => {
    e.preventDefault();

    const input = document.querySelector('.autocomplete-input');
    const inputValue = input.value; 
    input.value = '';

    let user = user_list.filter(item => item.username === inputValue);
    if (isNullOrUndefined(user) || user.length <= 0) {
      return;
    }
    user = user[0];

    orgUtils.confirmationPrompt({
      title: 'Are you sure?',
      content: '<p>This will invite the user to your organisation</p>',
      onAccept: () => {
        fetch(getCurrentURL(), {
          method: 'POST',
          cache: 'no-cache',
          credentials: 'same-origin',
          withCredentials: true,
          headers: {
            'X-Target': 'invite_member',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': token,
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            ...user,
            oid: data.oid
          })
        })
          .then(response => response.json())
          .then(response => renderInvitesList(root, token, null))
      }
    });
  });

  for (let i = 0; i < active_invites.length; i++) {
    const obj = active_invites[i];
    const [card] = composeTemplate(templates.invite, {
      params: {
        userid: obj.user_id,
        name: obj.username,
      },
      modify: [{
        select: 'span',
        parent: invitesList
      }]
    });

    const delete_btn = card.querySelector(`[data-target="delete"]`);
    delete_btn.addEventListener('click', (e) => {
      orgUtils.confirmationPrompt({
        title: 'Are you sure?',
        content: '<p>This will rescind the invite to your organisation</p>',
        onAccept: () => {
          fetch(getCurrentURL(), {
            method: 'POST',
            cache: 'no-cache',
            credentials: 'same-origin',
            withCredentials: true,
            headers: {
              'X-Target': 'cancel_invite',
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': token,
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              uid: obj.user_id,
              oid: data.oid
            })
          })
            .then(response => response.json())
            .then(response => renderInvitesList(root, token, null))
        }
      });
    });
  }
}

domReady.finally(() => {
  const root = document.querySelector('#root');
  const token = getCookie('csrftoken');
  
  const member_data = JSON.parse(
    root.querySelector('script[for="organisation-members"]').innerText.trim()
  );
  renderMembersList(root, token, member_data);
  
  const invite_data = JSON.parse(
    root.querySelector('script[for="organisation-invites"]').innerText.trim()
  );
  renderInvitesList(root, token, invite_data);
});
