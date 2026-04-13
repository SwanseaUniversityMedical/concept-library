domReady.finally(() => {
  const copyToClipboard = async (value) => {
    const copyResult = await navigator.clipboard.writeText(value).then(() => true, () => false);
    if (!copyResult) {
      throw new Error("Failed to copy text");
    }

    return true;
  };

  document.body.addEventListener('click', (e) => {
    const trg = e.target;
    if (!trg.matches('.copy-area__button')) {
      return;
    }

    const area = trg.parentElement;
    const input = area.querySelector('input[readonly]');
    if (!input) {
      return;
    }

    const state = area.getAttribute('data-state');
    const copying = area.getAttribute('data-copying');
    if (state !== 'copyable' || copying !== null) {
      return;
    }
    area.setAttribute('data-copying', true);

    copyToClipboard(input.value)
      .then(() => {
        area.setAttribute('data-state', 'success');
        window.ToastFactory.push({
          type: 'success',
          message: 'Copied to clipboard',
          duration: 600,
        });
        setTimeout(() => {
          area.setAttribute('data-state', 'copyable');
        }, 600);
      })
      .catch((e) => {
        area.setAttribute('data-state', 'failure');
        window.ToastFactory.push({
          type: 'error',
          message: 'Failured to copy to clipboard',
          duration: 1200,
        });
        setTimeout(() => {
          area.setAttribute('data-state', 'copyable');
        }, 1200);
      })
      .finally(() => {
        area.removeAttribute('data-copying');
        input.select();
      });
  });
});