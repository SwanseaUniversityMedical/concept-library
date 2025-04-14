domReady.finally(() => {
  const ctrlKeys = [
    'KeyA', 'KeyF', 'KeyX',
    'KeyZ', 'KeyY', 'KeyC',
    'Backspace', 'Delete'
  ];

  createGlobalListener(
    'inputs.number:keydown',
    'input.number-input__group-input[type="number"]',
    (e) => {
      const target = e.target;
      const keyCode = e.which ?? e.keyCode;
      if (!keyCode || (keyCode >= 8 && keyCode <= 46) || (e.ctrlKey && ctrlKeys.includes(e.code))) {
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

      let allowed = (
        (keyCode >= 48 && keyCode <= 57) ||
        (keyCode >= 96 && keyCode <= 105) ||
        keyCode === 173
      );

      if (datatype !== 'int') {
        allowed = allowed || keyCode === 190;
      }

      if (!allowed) {
        e.preventDefault();
        return true;
      }

      return false;
    }
  );

  createGlobalListener(
    'inputs.number:paste',
    'input.number-input__group-input[type="number"]',
    (e) => {
      e.preventDefault();

      let paste = (e.clipboardData || window.clipboardData).getData('text');
      paste = paste.toUpperCase().trim().replace(/[^\-\d\.]/gmi, '');
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

      const input = trg?.parentElement?.parentElement?.querySelector?.('input.number-input__group-input');
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

      let value, diff;
      switch (datatype) {
        case 'int': {
          diff = parseInt(step);
          if (isNaN(diff)) {
            diff = 1;
            step = '1';
          }

          value = parseInt(input.value.trim());
        } break;

        case 'float':
        case 'numeric':
        case 'decimal':
        case 'percentage': {
          diff = parseFloat(step);
          if (isNaN(diff)) {
            diff = 0.1;
            step = '0.1';
          }

          value = parseFloat(input.value.trim());
        } break;

        default:
          value = null;
          break;
      }

      if (isNullOrUndefined(value) || isNaN(value)) {
        value = 0;
      }

      value += diff*(opr === 'decrement' ? -1 : 1);
      if (datatype === 'int') {
        value = Math.trunc(value);
      } else {
        const m = Math.pow(10, step.split('.')?.[1]?.length || 0);
        value = Math.round(value * m) / m;
      }

      input.value = value;
      fireChangedEvent(input);

      return true;
    }
  );
});
