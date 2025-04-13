domReady.finally(() => {
  createGlobalListener(
    'inputs.number:keydown',
    'input.number-input__group-input[type="number"]',
    (e) => {
      const target = e.target;
      const keyCode = e.which ?? e.keyCode;
      if (!keyCode || (keyCode >= 8 && keyCode <= 46) || ((keyCode === 86 || keyCode === 65) && e.ctrlKey)) {
        return true;
      }

      if (e.shiftKey) {
        e.preventDefault();
        return false;
      }

      let datatype = target.getAttribute('data-type');
      if (!stringHasChars(datatype)) {
        datatype = 'numeric';
      } else {
        datatype = datatype.trim().toLowerCase();
      }

      let allowed = (keyCode >= 48 && keyCode <= 57) || (keyCode >= 96 && keyCode <= 105);
      if (datatype !== 'int') {
        allowed = allowed || keyCode === 190;
      }

      if (!allowed) {
        e.preventDefault();
        return false;
      }

      return true;
    }
  );

  createGlobalListener(
    'inputs.number:paste',
    'input.number-input__group-input[type="number"]',
    (e) => {
      e.preventDefault();

      let paste = (e.clipboardData || window.clipboardData).getData('text');
      paste = paste.toUpperCase().trim().replace(/[^\d\.]/gmi, '');
      paste = Number(paste)

      if (!isNaN(paste)) {
        e.target.value = paste
      } else {
        e.target.value = null;
      }

      return false;
    }
  );

  createGlobalListener(
    'inputs.number:click',
    'button.number-input__group-action',
    (e) => {
      e.preventDefault();

      const trg = e.target;
      const opr = trg.getAttribute('data-op').trim().toLowerCase();

      const input = trg?.parentElement?.parentElement?.querySelector('input.number-input__group-input[type="number"]');
      if (!input) {
        return false;
      }

      let datatype = input.getAttribute('data-type');
      if (!stringHasChars(datatype)) {
        datatype = 'numeric';
      } else {
        datatype = datatype.trim().toLowerCase();
      }

      let step = input.getAttribute('data-step');
      step = stringHasChars(step) ? step.trim() : input.getAttribute('step')?.trim?.();

      let value;
      switch (datatype) {
        case 'int': {
          step = parseInt(step);
          step = !isNaN(step) ? step : 1;

          value = parseInt(value);
        } break;

        case 'float':
        case 'numeric':
        case 'decimal':
        case 'percentage': {
          step = parseFloat(step);
          step = !isNaN(step) ? step : 0.1;

          value = parseFloat(value);
        }

        default:
          value = null;
          break;
      }

      if (isNullOrUndefined(value) || isNaN(value)) {
        return false;
      }

      target.value = value + step*(opr === 'decrement' ? -1 : 1);
      return true;
    }
  );
});
