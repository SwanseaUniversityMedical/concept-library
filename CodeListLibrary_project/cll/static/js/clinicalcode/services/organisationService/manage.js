import * as orgUtils from './utils.js';
import { Autocomplete } from '../../components/autocomplete.js';

const renderMembersList = (root, token, data, uid) => {
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
      .then(response => renderMembersList(root, token, response.members, uid))
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
      parent: memberList,
      render: (elems) => {
        const [tr] = elems;
        const roleContainer = tr.querySelector('#member-role-container');

        let [btn] = composeTemplate(templates.dropdown, {
          params: {
            uid: obj.user_id,
          }
        });
        btn = roleContainer.appendChild(btn);
        btn.disabled = (uid === obj.user_id);

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
      sanitiseTemplate: false
    });
    
    const delete_btn = card.querySelector(`[data-target="delete"]`);
    delete_btn.disabled = (uid === obj.user_id);
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
            .then(response => renderMembersList(root, token, null, uid))
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
      parent: invitesList,
      sanitiseTemplate: false
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
  
  const data = root.querySelector('script[for="organisation-members"]');
  const member_data = JSON.parse(
    data.innerText.trim()
  );
  const user_id = parseInt(data.getAttribute('uid'));
  renderMembersList(root, token, member_data, user_id);
  
  const invite_data = JSON.parse(
    root.querySelector('script[for="organisation-invites"]').innerText.trim()
  );
  renderInvitesList(root, token, invite_data);
});
