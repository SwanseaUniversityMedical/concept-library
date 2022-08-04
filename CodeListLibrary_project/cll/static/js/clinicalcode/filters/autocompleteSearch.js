var AUTOKEYS = {
  ENTER: 13,
  DOWN: 40,
  UP: 38
}

$.fn.autocompleteSearch = function (methods) {
  var $input = $(this);
  var currentFocus = -1;
  var namespace = generateUUID();

  var closeAutocomplete = (elem) => {
    currentFocus = -1;
    
    $('.autocomplete_items').each((k, v) => {
      if (typeof elem === 'undefined' || $(elem).parents($(v).parent())) {
        $(v).remove();
      }
    });
  }

  var popActive = () => {
    var $autocomplete = $input.parent().find('#' + namespace + '_list');
    if ($autocomplete[0]) {
      $autocomplete.children('div').each((k, v) => {
        $(v).removeClass('autocomplete_active');
      });
    }
  }

  var pushActive = () => {
    popActive();
    
    var $autocomplete = $input.parent().find('#' + namespace + '_list');
    if ($autocomplete[0]) {
      var $children = $autocomplete.children('div');
      currentFocus = currentFocus < 0 
                      ? ($children.length - 1) 
                      : (currentFocus >= $children.length 
                          ? 0 
                          : currentFocus);
      
      $($children[currentFocus]).addClass('autocomplete_active');
    }
  }

  var runQuery = () => {
    closeAutocomplete();

    var needle = $input.val();
    var results = methods.onQuery(needle, this);
    if (results.length < 1)
      return;
    
    var $autocomplete = $('<div id="' + namespace + '_list" class="autocomplete_items"></div>');
    $.each(results, (k, v) => {
      var $element = $('<div id="autocomplete_item_' + namespace + '">' + v + '</div>');
      $autocomplete.append($element);
      $element.on('click', function (e) {
        var selected = $element.text().trim();
        $input.val(selected);
        methods.onSelected(selected, this);
        closeAutocomplete();
      });
    });
    $input.parent().append($autocomplete);
  }

  var isFocused = false;
  $(document).on('click.' + namespace, function (e) {
    var $element = $(e.target);
    if (!$element.prop('id').includes(namespace)) {
      if ($input.parent().find('#' + namespace + '_list').length > 0) {
        closeAutocomplete($input);
      }
    }
    
    if ($element.prop('id') == $input.prop('id')) {
      isFocused = true;
      runQuery();
    } else {
      if (isFocused) {
        isFocused = false;
        methods.onFocusLost($input);
      }
    }
  });

  $input.bind('keydown.' + namespace, (e) => {
    var keycode = e.keyCode;
    switch (keycode) {
      case AUTOKEYS.ENTER:
        e.preventDefault();

        if (currentFocus > -1) {
          var $autocomplete = $input.parent().find('#' + namespace + '_list');
          if ($autocomplete[0]) {
            var $children = $autocomplete.children('div');
            $($children[currentFocus]).click();
            return;
          }
        }

        runQuery();

        break;
      case AUTOKEYS.DOWN:
      case AUTOKEYS.UP:
        currentFocus += (keycode == AUTOKEYS.UP ? -1 : 1);
        pushActive();
        break;
      default:
        runQuery();
        break;
    }
  });

  $input.data('autocompleteSearch', {
    namespace: namespace,
    unbind: () => {
      $input.unbind('keydown.' + namespace);
      $(document).unbind('click.' + namespace);
    }
  });
  
  return this;
}