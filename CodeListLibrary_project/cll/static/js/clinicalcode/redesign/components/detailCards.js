const displayCardDetails = (elem) => {
  const id = elem.getAttribute('data-entity-id');
  const version = elem.getAttribute('data-entity-version-id');
  if (!id || !version) {
    return;
  }
  
  window.location.replace(`/ge/${id}/version/${version}/detail`);
}
