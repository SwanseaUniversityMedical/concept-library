var phenotype_types = typeof phenotype_types === 'undefined' ? [] : phenotype_types;
var type_names = typeof type_names === 'undefined' ? [] : type_names;
var all_phenotypes = typeof all_phenotypes === 'undefined' ? [] : all_phenotypes;

/* Global defs */
var PAGE = {
  PHENOTYPE: 0,
  CONCEPT: 1
}

var RESULT_QUERIES = ['20', '50', '100'];
var TEXT_QUERIES = ['search1', 'author_text', 'owner_text'];
var DISPLAY_QUERIES = {
  [PAGE.PHENOTYPE]: ['show_deleted_phenotypes', 'show_my_phenotypes',
                      'phenotype_must_have_published_versions', 'show_mod_pending_phenotypes', 
                      'show_my_pending_phenotypes', 'show_rejected_phenotypes'
                    ],
  [PAGE.CONCEPT]: ['show_deleted_concepts', 'show_my_concepts', 
                    'show_only_validated_concepts', 'must_have_published_versions']
};

var baseFilters = {
  tags: {
    name: 'tags',
    searchbar: '#tag_searchbar',
    haystack: tag_names,
    reference: all_tag_ref
  },
  collections: {
    name: 'collection',
    searchbar: '#collection_searchbar',
    haystack: collection_names,
    reference: all_collections
  },
  coding: {
    name: 'coding',
    searchbar: '#coding_searchbar',
    haystack: coding_names,
    reference: all_coding
  },
};

var SEARCHBARS = {
  [PAGE.CONCEPT]: baseFilters,
  [PAGE.PHENOTYPE]: Object.assign({
    types: {
      name: 'types',
      searchbar: '#type_searchbar',
      haystack: type_names,
      reference: all_phenotypes
    },
  }, baseFilters)
};

/* Inject dependencies */
var environment = document.currentScript;
var dependencies = [];
$.each(environment.attributes, (i, attr) => {
  if (attr.name.includes('req-')) {
    var cls = attr.name.split('-')[1];
    var dep = attr.value.split(',');
    $.each(dep, (i, v) => {
      dependencies.push([cls, v]);
    });
  }
});

var preload = [];
for (var i = 0; i < dependencies.length; i++) {
  var cls = dependencies[i][0];
  var url = dependencies[i][1];
  switch (cls) {
    case 'scripts': {
      preload.push(new Promise((resolve, reject) => {
        $.ajax({
          dataType: 'script',
          cache: true,
          url: url,
          success: function (data) {
            if (data) {
              $.globalEval(data);
              resolve({success: true});
            } else {
              reject({no_response: true});
            }
          },
          error: function (ex) {
            reject({error: ex});
          }
        });
      }));
      
      break;
    }
    case 'styles': {
      $('<style type="text/css">@import url("' + url + '")</style>')
        .prependTo('body');
      
      preload.push(Promise.resolve({success: true}));
      
      break;
    }
    default:
      break;
  }
}

/* Utilities */
var isSubset = (arr1, arr2) => {
  return arr1.every(i => arr2.includes(i));
}

var generateUUID = () => {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

/* Filter Service */
var initFilters = () => {
  var library = PAGE[$(environment).attr('env')];

  if (typeof library === 'undefined') {
    return console.warn('FilterService unable to initialise in current environment');
  }

  // Toast notifications for errors or info post-AJAX
  var notifications = []
  var pushToastNotification = (style, desc) => {
    for (var i = 0; i < notifications.length; i++) {
      var $notifcation = $(notifications[i]);
      $notifcation.css('bottom', ((i + 1) * 90 - (i * 30)).toString() + 'px');
    }

    var uuid = generateUUID();
    var $toast = $('<div class="filter_toast push" type=' + style + ' style="bottom: 30px" name=' + uuid + '><span id="icon"></span><div id="desc">' + desc + '</div></div>');
    $('.toast_holder').append($toast);
    notifications.push($toast[0]);

    setTimeout(function () {
      var prev = notifications.length;
      notifications = notifications.filter((item) => {
        return $(item).attr('name') !== uuid;
      });

      for (var i = 0; i < notifications.length; i++) {
        var $notifcation = $(notifications[i]);
        $notifcation.css('bottom', ((i + 1) * 30 + (i * 30)).toString() + 'px');
      }

      $toast.remove();
    }, 6400);
  }

  // Typeahead searchbar to minify lists
  var typeaheadSearchbar = (input, query, typingDelay = 500) => {
    var namespace = '.' + generateUUID();

    var $input = $(input);
    var runQuery = () => {
      query($input, $input.val());
    }

    var timer;
    $input.bind('keyup' + namespace, (e) => {
      clearTimeout(timer);
      if (e.keyCode == 13) {
        e.preventDefault();
        runQuery();
      } else {
        timer = setTimeout(runQuery, typingDelay)
      }
    });

    $input.bind('keydown' + namespace, (e) => {
      clearTimeout(timer);
    });

    return {
      object: $input,
      namespace: namespace.replace('.', ''),
      unbind: () => {
        $input.unbind('keyup' + namespace);
        $input.unbind('keydown' + namespace);
      }
    }
  }

  // Date defs & utilities datepicker
  var base_start_date = moment('2018/01/01').startOf('day');
  var dateTime = moment();
  var dateValue = moment({
    year: dateTime.year(),
    month: dateTime.month(),
    day: dateTime.date()
  }).startOf('day');

  var dateRanges = {
    'All': [moment(base_start_date), moment(dateValue)],
    'Last Week': [moment(dateValue).subtract(6, 'days'), moment(dateValue)],
    'Last Month': [moment(dateValue).startOf('month'), moment(dateValue)],
    'Last 6 Months': [moment(dateValue).subtract(6, 'month').startOf('month'), moment(dateValue)],
    'Last Year': [moment(dateValue).subtract(1, 'year').add(1,'day'), moment(dateValue)],
  }

  var isBaseDateRange = (params) => {
    if (params['startdate'] === null && params['enddate'] === null) {
      return true;
    }

    var startdate = params['startdate'];
    var enddate = params['enddate'];
    return (startdate == base_start_date.format('YYYY-MM-DD') && enddate == dateValue.format('YYYY-MM-DD'));
  }
  
  // Parse current parameters from URL
  var order_by = '';
  var searchString = null;
  var selected_codes = [];
  var selected_phenotype_types = [];
  var selected_collections = [];
  var start = moment(base_start_date);
  var end = moment(dateValue);
  var rangeName = 'Custom Range';

  var fetchFilterParameters = (location) => {
    var params = new URL(location == undefined ? window.location.href : location);
    params.searchParams.forEach(function (value, key) {
      switch (key) {
        case "tagids":
          selected_collections = value.split(',');
          break;
        case "codingids":
          selected_codes = value.split(',');
          break;
        case "selected_phenotype_types":
          selected_phenotype_types = value.split(',')
          break;
        case "startdate":
          start = moment(value, 'YYYY-MM-DD');
          break;
        case "enddate":
          end = moment(value, 'YYYY-MM-DD');
          break;
        case "search":
          searchString = value;
          break;
        case "range":
          rangeName = value;
          break;
        case "order_by":
          order_by = order_by;
          break;
        default:
          break;
      }

      // Filter null cases
      selected_collections.filter(e => e !== '');
      selected_codes.filter(e => e !== '');
      selected_phenotype_types.filter(e => e !== '');

      // Set current input
      $("#basic-form input[name=" + key + "]").val(value);
    });

    if (library == PAGE.PHENOTYPE) {
      if (params.searchParams.get('selected_phenotype_types') == null) {
        selected_phenotype_types = [];
        $("#basic-form input[id=selected_phenotype_types]").val('');
        $(".filter_option.types").prop('checked', false);
      }
    }

    $.each(DISPLAY_QUERIES[library], (_, key) => {
      if (params.searchParams.get(key) == null) {
        $("#basic-form input[id=" + key + "]").val('0');
        $("#" + key + "_hidden").val('0');
        $("#" + key + ".form-checkbox").prop('checked', null);
      }
    });
    
    if (params.searchParams.get('page_size') == null || !RESULT_QUERIES.includes(params.searchParams.get('page_size'))) {
      var $results = $('.number_filter li').first().text();
      $('#filter_number_option span').text($results);
      $("#basic-form input[id=page_size]").val($results);
    }

    if (params.searchParams.get('order_by') == null) {
      var $order = $('.order_filter li').first().text();
      $('#filter_order_option span').text($order);
      $("#basic-form input[id=order_by]").val($order);
      order_by = $order;
    }

    if (params.searchParams.get('search') == null) {
      searchString = null;
      $("#basic-form input[name=search]").val('');
    }

    if (params.searchParams.get('page') == null) {
      $("#basic-form input[id=page]").val('1');
    }

    if (params.searchParams.get('owner') == null) {
      $("#basic-form input[name=owner]").val('');
      $('#owner_text').val('');
    }

    if (params.searchParams.get('author') == null) {
      $("#basic-form input[name=author]").val('');
      $('#author_text').val('');
    }

    if (params.searchParams.get('codingids') == null) {
      selected_codes = [];
      $("#basic-form input[id=codingids]").val('');
      $(".filter_option.coding").prop('checked', false);
    }

    if (params.searchParams.get('tagids') == null) {
      selected_collections = [];
      $("#basic-form input[id=tagids]").val('');
      $(".filter_option.collection").prop('checked', false);
      $(".filter_option.tags").prop('checked', false);
    }

    if (params.searchParams.get('startdate') == null || params.searchParams.get('enddate') == null) {
      start = moment(base_start_date);
      end = moment(dateValue);
      $("#basic-form input[id=startdate]").val(start.format('YYYY-MM-DD'));
      $("#basic-form input[id=enddate]").val(end.format('YYYY-MM-DD'));
    }

    for (var range in dateRanges) {
      if (start.format('YYYY-MM-DD') == dateRanges[range][0].format('YYYY-MM-DD') && end.format('YYYY-MM-DD') == dateRanges[range][1].format('YYYY-MM-DD')) {
        rangeName = range;
        break;
      }
    }

    var $picker = $('#filter_date').data('daterangepicker');
    if ($picker !== undefined) {
      $picker.startDate = start;
      $picker.endDate = end;
      $picker.calculateChosenLabel();

      if (rangeName == 'Custom Range') {
        $('#filter_date span').html(start.format('DD MMM YY') + ' - ' + end.format('DD MMM YY'));
      } else {
        $('#filter_date span').html(rangeName);
      }
    }
  }

  fetchFilterParameters();

  // Handle scroll to top button(s)
  $(document).on('click', '#scroll_up', (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Handle collapsible state of filter option(s)
  $('.collapse').each(function (i, obj) {
    var anchor = $(document).find('a[href^="#' + this.id + '"]')[0];
    if (typeof anchor !== 'undefined') {
      var icons = $(anchor).find('.morphing_caret')[0];
      if (typeof icons !== 'undefined') {
        // Toggle animation
        $(obj).on('show.bs.collapse', function () {
          $(icons).toggleClass('closed');
        });
        $(obj).on('hide.bs.collapse', function () {
          $(icons).toggleClass('closed');
        });
      }
    }
  });

  // Animate loading icon on ajax timeout after 0.5s
  var loadingTimeout;
  $(document).on({
    ajaxStart: function () {
      loadingTimeout = setTimeout(function () {
        $('#loading_res_spinner').removeClass('hidden');
        $('#result-div').html('');
      }, 500);
    },
    ajaxStop: function () {
      $('#loading_res_spinner').addClass('hidden');
      clearTimeout(loadingTimeout);
    }
  });

  // Handle ajax req. for updating concept & phenotype results
  var cancellablePromise = promise => {    
    var rejected;
    var wrapped = new Promise((resolve, reject) => {
      rejected = reject;
      Promise.resolve(promise).then(resolve).catch(reject);
    });

    wrapped.cancel = () => {
      // Cancel loading animation state
      $('#loading_res_spinner').addClass('hidden');
      clearTimeout(loadingTimeout);

      // Pass cancellation
      rejected({canceled: true});
    }

    return wrapped;
  }

  var currentQuery;
  var getFilterResults = (target, values) => {
    if (currentQuery) {
      currentQuery.cancel();
    }

    var getResults = new Promise((resolve, reject) => {
      $.ajax({
        url: '',
        type: 'GET',
        data: Object.assign({}, {'filtermethod': target}, values),
        dataType: 'html',
        success: function (data) {
          if (data) {
            resolve(data);
          } else {
            reject({no_response: true});
          }
        },
        error: function (err) {
          reject(err);
        }
      });
    })

    currentQuery = cancellablePromise(getResults);
    return currentQuery;
  }
  
  $('#basic-form').on('submit', function (e, method) {
    if (typeof method == 'undefined' || typeof method.element == 'undefined')
      return;
    
    e.preventDefault();

    var values = { };
    if (method.element == 'search') {
      $("#basic-form input[id=page]").val(1);
    }
    
    $('#basic-form :input').each(function() {
      if (this.name != 'search_button') {
        if (this.name == 'search') {
          var searchQuery;
          if (method.element == 'search') {
            searchQuery = $(this).val();
          } else {
            searchQuery = searchString;
          }

          if (typeof searchQuery !== 'undefined' && searchQuery !== null) {
            values[this.name] = searchQuery;
            searchString = searchQuery;
          }
        } else {
          values[this.name] = $(this).val();
        }
      }
    });
    
    getFilterResults($(e.target)[0].id, values)
      .then((data) => {
        // Update results
        $('#result-div').html(data);

        // Update result counter
        $('#result_count').text($('#result-div #paginator_count').text() + ' Record(s)');

        // Update URL parameters --> Only update url parameter if url is defined & if parameter is not the base value
        var url = new URL(window.location.href);
        $.each(values, function (key, value) {
          var is_defined = (typeof value !== 'undefined' && value !== '' && value !== '-1' && value !== '0' && value !== 'basic-form');
          var is_not_base = (
            !(key == 'page' && value == '1')
              && !(key == 'order_by' && value == $('.order_filter li').first().text())
              && !((key == 'startdate' || key == 'enddate') && isBaseDateRange(values))
              && !(key == 'page_size' && (value == $('.number_filter li').first().text() || !RESULT_QUERIES.includes(value)))
          );
          
          if (is_defined && is_not_base) {
            url.searchParams.set(key, value);
          } else {
            url.searchParams.delete(key);
          }
        });

        // Apply history to window if page, search query or date is changed, otherwise replace state to avoid unnecessary window hx upd
        if (method.element == 'page' || method.element == 'search' || method.element == 'date') {
          window.history.pushState({}, document.title, '?' + url.searchParams);
        } else {
          window.history.replaceState({}, document.title, '?' + url.searchParams);
        }
      })
      .catch((error) => {
        console.log(error);
        if (typeof error === 'object' && typeof error['canceled'] !== 'undefined') {
          return;
        }

        pushToastNotification('error', 'An error has occurred when filtering results.');
      })
      .finally(() => {
        fetchFilterParameters();
      })
  });

  // Handle pop & push states on filter, and when leaving page
  $(window).bind('popstate', (e) => {
    location.reload();
  });

  // Handle filter clear & refresh buttons
  $('#refresh_filters').on('click', (e) => {
    $("#basic-form").trigger('submit', [{'element': 'refresh'}]);
  });

  $('#clear_filters').on('click', (e) => {
    var url = location.protocol + '//' + location.host + location.pathname;
    fetchFilterParameters(url);
    $("#basic-form").trigger('submit', [{'element': 'search'}]);
  });

  // Handle results per page option
  $(document).on('click', '.number_filter a', (e) => {
    e.preventDefault();

    var $results = $(e.target).text();
    $('#filter_number_option span').text($results);
    $("#basic-form input[id=page_size]").val($results);
    $("#basic-form").trigger('submit', [{'element': 'page_size'}]);
  });

  // Handle ordering option
  $(document).on('click', '.order_filter a', (e) => {
    e.preventDefault();

    var $order = $(e.target).text();
    order_by = $order;

    $('#filter_order_option span').text($order);
    $("#basic-form input[id=order_by]").val($order);
    $("#basic-form").trigger('submit', [{'element': 'order'}]);
  });

  // Date range filter option & initialising current date selection
  var initialisedDate = false;
  var setDateRange = (start, end, period) => {
    switch (period) {
      case "Custom Range": {
        $('#filter_date span').html(start.format('DD MMM YY') + ' - ' + end.format('DD MMM YY'));
        break;
      }
      default: {
        $('#filter_date span').html(period);
        break;
      }
    }

    if (initialisedDate) {
      $("#basic-form input[id=page]").val(1);
      $("#basic-form input[id=startdate]").val(start.format('YYYY-MM-DD'));
      $("#basic-form input[id=enddate]").val(end.format('YYYY-MM-DD'));
      $("#basic-form").trigger('submit', [{'element': 'date'}]);
    } else {
      initialisedDate = true;
    }

    rangeName = period;
  }

  setDateRange(start, end, rangeName);

  $('#filter_date').daterangepicker({
    startDate: start,
    endDate: end,
    drops: 'auto',
    showDropdowns: true,
    maxYear: dateValue.year(),
    ranges: dateRanges,
  }, setDateRange);

  // Override search bar and authorship options, incl. any assoc. buttons
  $.each(['author_text', 'owner_text'], (i, selector) => {
    $('#' + selector).focusout((e) => {
      var $target = $(e.target);
      var $name = $target.attr('name');
      switch ($name) {
        case "author":
          $("#basic-form input[name=author]").val($target.val());
          break;
        case "owner":
          $("#basic-form input[name=owner]").val($target.val());
          break;
        default:
          break;
      }
      
      $("#basic-form").trigger('submit', [{'element': $name}]);
    });
  });
  
  $(document).on('keypress', function (e) {
    if (e.keyCode == 13) {
      e.preventDefault();

      var $target = $(e.target)
      var $name = $target.attr('name');
      if (!TEXT_QUERIES.includes($target.attr('id'))) {
        return;
      }

      switch ($name) {
        case "author":
          $("#basic-form input[name=author]").val($target.val());
          break;
        case "owner":
          $("#basic-form input[name=owner]").val($target.val());
          break;
        default:
          break;
      }

      $("#basic-form").trigger('submit', [{'element': $name}]);
    }
  });

  $('#search_btn').on('click', function (e) {
    e.preventDefault();
    
    $("#basic-form").trigger('submit', [{'element': 'search'}]);
  });

  // Reroute pagination to ajax submission form
  $(document).on('click', '.btn-paginate', function (e) {
    e.preventDefault();

    var dest = parseInt($(this).attr('value'));
    $("#basic-form input[id=page]").val(dest);
    $("#basic-form").trigger('submit', [{'element': $(this).attr('name')}]);
    window.scrollTo({ top: 0 });
  });

  // Initialise searchbars for long list filter(s)
  $.each(SEARCHBARS[library], (key, group) => {
    typeaheadSearchbar(group.searchbar, ($input, query) => {
      var $tags = $('#filter_by_' + group.name + ' .' + group.name);
      var $holder = $tags.first().parent().parent().parent();
      var $children = $holder.children('li');

      if (query === '') {
        // Show all, with checked appearing at top of list (else alphabetical order)
        $holder.find('#filter_no_result').first().addClass('hide');

        $tags.each((key, element) => {
          $(element).parent().parent().removeClass('hide');
        });

        $children.detach().sort(function (a, b) {
          var v1 = $(a).find('input').first();
          var v2 = $(b).find('input').first();
          if (v1.prop('checked') && !v2.prop('checked')) {
            return -1;
          } else if (v2.prop('checked') && !v1.prop('checked')) {
            return 1;
          } else {
            var n1 = $(a).find('.form-check-label').first().text().trim().toLocaleLowerCase();
            var n2 = $(b).find('.form-check-label').first().text().trim().toLocaleLowerCase();
            if (n1 < n2) {
              return -1;
            } else if (n1 > n2) {
              return 1;
            }
          }

          return 0;
        });
        $holder.append($children);
      } else {
        var results = FuzzyQuery.Search(group.haystack, query, FuzzyQuery.Results.SORT, FuzzyQuery.Transformers.IgnoreCase);
        if (results.length <= 0) {
          // Display 'no results' banner
          $holder.find('#filter_no_result').first().removeClass('hide');
        } else {
          $holder.find('#filter_no_result').first().addClass('hide');
        }

        // Display results in order of proximity
        var selected = { };
        results.map((e, i) => {
          var item = group.reference.find(x => x.name.toLocaleLowerCase() === e.item.toLocaleLowerCase());
          if (item !== undefined && item !== null) {
            selected[item.id] = e.score;
          }
        });

        $tags.each((key, element) => {
          var $element = $(element);
          var value = $element.val();
          if (selected[value] !== undefined) {
            $element.parent().parent().removeClass('hide');
          } else {
            $element.parent().parent().addClass('hide');
          }
        });

        $children.detach().sort(function (a, b) {
          if ($(a).hasClass('hide') && $(b).hasClass('hide')) {
            return 0;
          } else if ($(a).hasClass('hide')) {
            return 1;
          } else if ($(b).hasClass('hide')) {
            return -1;
          }
          
          var v1 = $(a).find('input').first().val();
          var v2 = $(b).find('input').first().val();
          var s1 = selected[v1];
          var s2 = selected[v2];
          if (s1 < s2) {
            return -1;
          }
          if (s1 > s2) {
            return 1;
          }

          return 0;
        });
        $holder.append($children);
      }
    }, 300);
  });

  // Handles filtering options for types, collection, tags & coding systems
  $(".filter_option").change(function() {
    if($(this).prop('id') == 'checkAll_collection'){
      $(".filter_option.collection").prop('checked', $(this).prop('checked'));
    }else if($(this).prop('id') == 'checkAll_coding'){
      $(".filter_option.coding").prop('checked', $(this).prop('checked'));
    }else if($(this).prop('id') == 'checkAll_tags'){
      $(".filter_option.tags").prop('checked', $(this).prop('checked'));
    }else if($(this).prop('id') == 'checkAll_types'){
      $(".filter_option.types").prop('checked', $(this).prop('checked'));
    }else{				
      if($(this).prop('name') == 'collection_id'){
        if(!$(this).prop('checked')){
          if($("#checkAll_collection").prop('checked')){
            $("#checkAll_collection").prop('checked', false);
          }
        }
      }else if($(this).prop('name') == 'tag_id'){
        if(!$(this).prop('checked')){
          if($("#checkAll_tags").prop('checked')){
            $("#checkAll_tags").prop('checked', false);
          }
        }
      }else if($(this).prop('name') == 'coding_id'){
        if(!$(this).prop('checked')){
          if($("#checkAll_coding").prop('checked')){
            $("#checkAll_coding").prop('checked', false);
          }
        }
      }else if($(this).prop('name') == 'type_name'){
        if(!$(this).prop('checked')){
          if($("#checkAll_types").prop('checked')){
            $("#checkAll_types").prop('checked', false);
          }
        }
      }
    }
  
    selected_codes = [];
    $("input:checkbox[name=coding_id]:checked").each(function() {
      selected_codes.push(parseInt($(this).val()));
    });

    selected_collections = []
    $("input:checkbox[name=collection_id]:checked").each(function(){
      selected_collections.push(parseInt($(this).val()));
    });
    $("input:checkbox[name=tag_id]:checked").each(function(){
      selected_collections.push(parseInt($(this).val()));
    });
    
    
    $("#basic-form input[id=page]").val(1);

    if (library == PAGE.PHENOTYPE) {
      selected_phenotype_types = []
      $("input:checkbox[name=type_name]:checked").each(function(){
        selected_phenotype_types.push($(this).val());
      });

      if(isSubset(phenotype_types, selected_phenotype_types)){
        $("#checkAll_types").prop('checked', true);
      }

      $("#basic-form input[id=selected_phenotype_types]").val(selected_phenotype_types.join(','));
    }

    if(isSubset(brand_associated_collections_ids, selected_collections)){
      $("#checkAll_collection").prop('checked', true);
    }

    if(isSubset(brand_associated_tags_ids, selected_collections)){
      $("#checkAll_tags").prop('checked', true);
    }

    if(isSubset(coding_system_reference_ids, selected_codes)) {
      $("#checkAll_coding").prop('checked', true);
    }

    $("#basic-form input[id=tagids]").val(selected_collections);
    $("#basic-form input[id=codingids]").val(selected_codes);
    $("#basic-form").trigger('submit', [{'element': $(this).attr('name')}]);
  });
  
  // Change checkbox's hidden value when checked/unchecked
  $(".form-checkbox").change(function () {
    if ( $(this).is(":checked") ) {
      $("#" + $(this).attr('id') + "_hidden").val('1');
    } else if ( $(this).not(":checked") ) {
      $("#" + $(this).attr('id') + "_hidden").val('0');
    }
    
    $("#basic-form").trigger('submit', [{'element': 'display'}]);
  });

  // Filter modal button for mobile devices
  var $filter_panel = $('#filter_panel_group');
  var $filter_modal = $('#filter-modal');
  $filter_modal.on('shown.bs.modal', (e) => {
    $filter_panel.find('#filter_form').first().appendTo($filter_modal.find('.modal-body').first());
    $filter_panel.find('.filter_buttons').first().appendTo($filter_modal.find('.modal-footer').first());
  });
  $filter_modal.on('hide.bs.modal', (e) => {
    $filter_modal.find('#filter_form').first().appendTo($filter_panel);
    $filter_modal.find('.filter_buttons').first().appendTo($filter_panel);
  });

  // Apply responsive style @ media query
  var $result_page = $('#result-div');
  var resizeResultPage = (win) => {
    if (win.width() < 1050) {
      $result_page.removeClass('col-sm-10');
      $result_page.addClass('col-sm-12');
    } else {
      $result_page.addClass('col-sm-10');
      $result_page.removeClass('col-sm-12');
    }
  }

  $(window).on('resize', function() {
    var win = $(this);
    resizeResultPage(win);
  });
  resizeResultPage($(window));
}

/* Initialise filters */
Promise.all(preload)
  .then(() => {
    $(document).ready(() => {
      initFilters();
    });
  })
  .catch((ex) => {
    console.warn(ex);
  });