const handleResponse = (token, invitation_reponse, redirect) => {
  fetch(getCurrentURL(), {
    method: 'POST',
    cache: 'no-cache',
    credentials: 'same-origin',
    withCredentials: true,
    headers: {
      'X-Target': 'invitation_reponse',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': token,
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      result: invitation_reponse
    })
  })
    .then(response => response.json())
    .then(response => {
      if (response.status) {
        window.location.href = redirect;
      }
    })
}

domReady.finally(() => {
  const token = getCookie('csrftoken');

  const acceptButton = document.querySelector('#accept-btn');
  acceptButton.addEventListener(
    'click', 
    e => handleResponse(token, true, acceptButton.getAttribute('data-href'))
  );

  const rejectButton = document.querySelector('#reject-btn');
  rejectButton.addEventListener(
    'click', 
    e => handleResponse(token, false, rejectButton.getAttribute('data-href'))
  );
});
