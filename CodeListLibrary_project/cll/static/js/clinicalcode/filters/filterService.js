/* Behaviour defs */
var FILTER_HIDE_WIDTH    = 1050; // Screen width, in px, to decide when to hide filter UI and replace with modal
var STICKY_OFFSET        = 10;   // Offset, in px, to determine when the sticky component should activate (relative to bottom of container) 
var STICKY_SPEED         = 20;   // How many pixels we move per frame until the container is within the viewport
var STICKY_INTERVAL      = 10;   // How many ms we wait per frame until moving the container
var SHOULD_TOGGLE_SEARCH = true; // Det. whether we should toggle filter search elements upon selection
var TAG_DECORATION       = {     // Det. decoration for 'Applied Filters' tag(s) for each type
  'author': {
    textColor: '#333',
    tagColor: '#FAF0D7',
    prefix: 'Author:',
  },
  'owner': {
    textColor: '#333',
    tagColor: '#FFD9C0',
    prefix: 'Owner:',
  },
  'search': {
    textColor: '#333',
    tagColor: '#E6D7F0',
    prefix: 'Search:',
  },
  'date': {
    textColor: '#333',
    tagColor: '#BAC1EC',
    prefix: 'Date:',
  },
  'selected_phenotype_types': {
    textColor: '#333',
    tagColor: '#FCDDAF',
    prefix: 'Type:',
  },
  'selected_workingset_types': {
    textColor: '#333',
    tagColor: '#FCDDAF',
    prefix: 'Type:',
  },
  'codingids': {
    textColor: '#333',
    tagColor: '#B5EAD7',
    prefix: 'Coding:',
  },
  'data_source_ids': {
    textColor: '#333',
    tagColor: '#8FCACA',
    prefix: 'Source:',
  },
  'collections': {
    textColor: '#333',
    tagColor: '#FEE8E2',
    prefix: 'Collection:',
  },
  'tags': {
    textColor: '#333',
    tagColor: '#D0E5B9',
    prefix: 'Tag:',
  },
};

/* Global defs */
var phenotype_types = typeof phenotype_types === 'undefined' ? [] : phenotype_types;
var type_names = typeof type_names === 'undefined' ? [] : type_names;
var all_phenotypes = typeof all_phenotypes === 'undefined' ? [] : all_phenotypes;
var data_source_reference = typeof data_source_reference === 'undefined' ? [] : data_source_reference;
var data_source_reference_ids = typeof data_source_reference_ids === 'undefined' ? [] : data_source_reference_ids;
var source_names = typeof source_names === 'undefined' ? [] : source_names;
var coding_names = typeof coding_names === 'undefined' ? [] : coding_names;
var all_coding = typeof all_coding === 'undefined' ? [] : all_coding;

var PAGE = {
  PHENOTYPE: 0,
  CONCEPT: 1,
  WORKINGSET: 2,
}

var RESULT_QUERIES = ['20', '50', '100'];
var TEXT_QUERIES = ['search1', 'author_text', 'owner_text'];
var DISPLAY_QUERIES = {
  [PAGE.PHENOTYPE]: ['show_deleted_phenotypes', 'show_my_phenotypes',
                      'phenotype_must_have_published_versions', 'show_mod_pending_phenotypes', 
                      'show_my_pending_phenotypes', 'show_rejected_phenotypes'
                    ],
  [PAGE.CONCEPT]: ['show_deleted_concepts', 'show_my_concepts', 
                    'show_only_validated_concepts', 'must_have_published_versions'],
  [PAGE.WORKINGSET]: ['show_my_ph_workingsets', 'show_deleted_ph_workingsets',
                      'show_my_pending_workingsets', 'show_mod_pending_workingsets', 
                      'show_rejected_workingsets', 'show_only_validated_workingsets', 'workingset_must_have_published_versions'
                    ],
};

var elementMap = {
  datasources: ['data_source_ids'],
  type: ['selected_phenotype_types', 'selected_workingset_types'],
  collection: ['collection_ids'],
  tags: ['tag_ids'],
  coding: ['codingids'],
  date: ['startdate', 'enddate'],
  authorship: ['author', 'owner'],
  publication: [
    // Pheno
    'show_rejected_phenotypes', 'show_my_pending_phenotypes', 'show_mod_pending_phenotypes',
    // Workingset
    'show_rejected_workingsets', 'show_my_pending_workingsets', 'show_mod_pending_workingsets'
  ],
  display: [
    // Concept
    'must_have_published_versions', 'show_only_validated_concepts', 'show_my_concepts', 'show_deleted_concepts', 
    // Phenotype
    'phenotype_must_have_published_versions', 'show_my_phenotypes', 'show_deleted_phenotypes',
    // Workingset
    'show_my_ph_workingsets', 'show_deleted_ph_workingsets', 'workingset_must_have_published_versions', 'show_only_validated_workingsets'
  ],
}

var subheaderMap = {
  data_source_ids: 'datasources',
  tag_ids: 'tags',
  collection_ids: 'collection',
  tags: 'tags',
  collections: 'collection',
  codingids: 'coding',
  enddate: 'date',
  startdate: 'date',
  selected_phenotype_types: 'type',
  selected_workingset_types: 'type',
  owner: 'authorship',
  author: 'authorship',
  show_deleted_phenotypes: 'display',
  show_my_phenotypes: 'display',
  phenotype_must_have_published_versions: 'display',
  show_mod_pending_phenotypes: 'publication',
  show_my_pending_phenotypes: 'publication',
  show_rejected_phenotypes: 'publication',
  show_deleted_concepts: 'display',
  show_my_concepts: 'display',
  show_only_validated_concepts: 'display',
  must_have_published_versions: 'display'
}

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
};

var SEARCHBARS = {
  [PAGE.CONCEPT]: Object.assign({
    coding: {
      name: 'coding',
      searchbar: '#coding_searchbar',
      haystack: coding_names,
      reference: all_coding
    },
  }, baseFilters),
  [PAGE.PHENOTYPE]: Object.assign({
    types: {
      name: 'types',
      searchbar: '#type_searchbar',
      haystack: type_names,
      reference: all_phenotypes
    },
    datasources: {
      name: 'datasources',
      searchbar: '#datasources_searchbar',
      haystack: source_names,
      reference: data_source_reference
    },
    coding: {
      name: 'coding',
      searchbar: '#coding_searchbar',
      haystack: coding_names,
      reference: all_coding
    },
  }, baseFilters),
  [PAGE.WORKINGSET]: Object.assign({
    types: {
      name: 'types',
      searchbar: '#type_searchbar',
      haystack: type_names,
      reference: all_phenotypes
    },
    datasources: {
      name: 'datasources',
      searchbar: '#datasources_searchbar',
      haystack: source_names,
      reference: data_source_reference
    },
  }, baseFilters),
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

/* Filter Service */
var initFilters = () => {
  var library = PAGE[$(environment).attr('env')];

  if (typeof library === 'undefined') {
    return console.warn('FilterService unable to initialise in current environment');
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

  // Filter Tag Service
  var toggleCheckState = (filterType, selected) => {
    $('.filter_option.' + subheaderMap[filterType]).each((i, elem) => {
      var isSelected = selected.includes($(elem).val());
      $(elem).prop('checked', isSelected);
    });
  }

  $('.applied_filter_tags').filterTags(
    TAG_DECORATION,
    {
      onHide: (element) => {
        $(element).parent().addClass('hide');
      },
      onShow: (element) => {
        $(element).parent().removeClass('hide');
      },
      onRemove: (element, filterType, filterValue) => {
        switch (filterType) {
          case 'tags':
            var selected = $("#basic-form input[id=tag_ids]").val().split(',').filter((x) => x != filterValue.value);
            $("#basic-form input[id=tag_ids]").val(selected.join(','));
            toggleCheckState(filterType, selected);
            break;
          case 'collections':
            var selected = $("#basic-form input[id=collection_ids]").val().split(',').filter((x) => x != filterValue.value);
            $("#basic-form input[id=collection_ids]").val(selected.join(','));
            toggleCheckState(filterType, selected);
            break;
          case 'date':
            start = moment(base_start_date);
            end = moment(dateValue);
            $("#basic-form input[id=startdate]").val('');
            $("#basic-form input[id=enddate]").val('');
            break;
          case 'datasources':
          case 'codingids':
          case 'selected_phenotype_types':
          case 'selected_workingset_types':
            var selected = $("#basic-form input[id=" + filterType + "]").val().split(',').filter((x) => x != filterValue.value);
            $("#basic-form input[id=" + filterType + "]").val(selected.join(','));
            toggleCheckState(filterType, selected);
            break;
          case 'owner':
          case 'author':
          case 'search':
            if (filterType === 'search') {
              searchString = '';
            }
            $("#basic-form input[name=" + filterType + "]").val('');
            break;
          default:
            var selected = $("#basic-form input[id=" + filterType + "]").val().replace(filterValue.value, '');
            $("#basic-form input[id=" + filterType + "]").val(selected);
            toggleCheckState(filterType, selected);
            break;
        }
        $("#basic-form").trigger('submit', [{'element': 'refresh'}]);
      },
    }
  );

  var filterDisplay = $('.applied_filter_tags').data('TagService');
  var parseTagsAndCollections = (value) => {
    var selected = value.split(',');
    var collections = all_collections.map((o) => o.id.toString()).filter(item => selected.includes(item));
    var tags = all_tag_ref.map((o) => o.id.toString()).filter(item => selected.includes(item));

    collections = collections.length > 0 ? collections : false;
    tags = tags.length > 0 ? tags : false;

    return {'collections': collections, 'tags': tags};
  }

  var parseReadableTag = (key, value) => {
    if (!isNaN(parseInt(value))) {
      var header = subheaderMap[key];
      var elements = $('#collapse-' + header).find('li input');
      for (var i = 0; i < elements.length; i++) {
        var $elem = $(elements[i]);
        if ($elem.val() === value) {
          var text = $elem.parent().find('span').text().trim();
          return {value: value, display: text};
        }
      }

      return {value: value, display: String(value)};
    }

    return {value: value};
  }

  var parseParameterAsTag = (filters, key, obj) => {
    if (obj.value.includes(',')) {
      filters[key] = obj.value.split(',').map(x => parseReadableTag(key, x));
    } else {
      filters[key] = parseReadableTag(key, obj.value);
    }
  }

  var selectActiveFilter = (url, mapped, cls) => {
    var active = 0
    for (var i = 0; i < mapped.length; i++) {
      var item = mapped[i];
      if (url.searchParams.get(item) !== null) {
        active++;
        break;
      }
    }

    if (active > 0) {
      $('a[href="#collapse-' + cls + '"] .filter_reset_btn').removeClass("hide");
    } else {
      $('a[href="#collapse-' + cls + '"] .filter_reset_btn').addClass("hide");
    }
  }

  var displayFiltersFromURL = (url) => {
    var filters = { };
    url.searchParams.forEach(function (value, key) {
      if (TAG_DECORATION[key]) {
        parseParameterAsTag(filters, key, {value: value});
      } else if (key === 'tag_ids' || key == 'collection_ids' || key == 'tag_collection_ids') {
        var selected = parseTagsAndCollections(value);
        if (selected.collections) {
          parseParameterAsTag(filters, 'collections', {value: selected.collections.join(',')});
        }
        if (selected.tags) {
          parseParameterAsTag(filters, 'tags', {value: selected.tags.join(',')});
        }
      }
    });

    var startRange = url.searchParams.get('startdate'),
        endRange = url.searchParams.get('enddate');
    if (startRange !== null && endRange !== null) {
      // Reformat date as dd/mm/yyyy and replace chars '-' with '/' before applying for human readability
      startRange = startRange.replace(/(\d{4})-(\d\d)-(\d\d)/, "$3/$2/$1");
      endRange = endRange.replace(/(\d{4})-(\d\d)-(\d\d)/, "$3/$2/$1");

      filters['date'] = {
        display: startRange + '<strong> \u2192 </strong>' + endRange,
        value: [startRange, endRange]
      };

      $('a[href="#collapse-date"] .filter_reset_btn').removeClass("hide");
    } else {
      $('a[href="#collapse-date"] .filter_reset_btn').addClass("hide");
    }

    // Handle individual filter reset
    if (url.searchParams.get('owner') == null && url.searchParams.get('author') == null) {
      $('a[href="#collapse-authorship"] .filter_reset_btn').addClass("hide");
    } else {
      $('a[href="#collapse-authorship"] .filter_reset_btn').removeClass("hide");
    }

    var _ignore = {
      startdate: true,
      enddate: true,
      owner: true,
      author: true,
      tags: true,
      collections: true,
    }

    $.each(subheaderMap, (i, v) => {
      if (typeof _ignore[i] === 'undefined' && v !== 'publication' && v !== 'display') {
        if (url.searchParams.get(i) !== null) {
          if (i === 'tag_collection_ids') {
            var selected = parseTagsAndCollections(url.searchParams.get(i));
            if (selected.collections) {
              $('a[href="#collapse-collection"] .filter_reset_btn').removeClass("hide");
            } else {
              $('a[href="#collapse-collection"] .filter_reset_btn').addClass("hide");
            }

            if (selected.tags) {
              $('a[href="#collapse-tags"] .filter_reset_btn').removeClass("hide");
            } else {
              $('a[href="#collapse-tags"] .filter_reset_btn').addClass("hide");
            }
          } else {
            $('a[href="#collapse-' + v + '"] .filter_reset_btn').removeClass("hide");
          }
        } else {
          if (i === 'tag_collection_ids') {
            $('a[href="#collapse-collection"] .filter_reset_btn').addClass("hide");
            $('a[href="#collapse-tags"] .filter_reset_btn').addClass("hide");
          } else {
            $('a[href="#collapse-' + v + '"] .filter_reset_btn').addClass("hide");
          }
        }
      }
    });

    selectActiveFilter(url, elementMap.display, 'display');
    selectActiveFilter(url, elementMap.publication, 'publication');

    filterDisplay.applyFilters(filters);
  }

  // Applies current parameters to URL
  var applyParametersToURL = (values) => {
    var url = new URL(window.location.href);
    $.each(values, function (key, value) {
      var is_defined = (typeof value !== 'undefined' && value !== '' && value !== '-1' && (key == 'selected_workingset_types' || value !== '0') && value !== 'basic-form');
      var is_not_base = (
        !(key == 'page' && value == '1')
          && !(key == 'order_by' && value == $('.order_filter li').first().text())
          && !((key == 'startdate' || key == 'enddate') && isBaseDateRange(values))
          && !(key == 'page_size' && (value.toString() == $('.number_filter li').first().text().toString() || !RESULT_QUERIES.includes(value.toString())))
      );
      
      if (is_defined && is_not_base) {
        url.searchParams.set(key, value);
      } else {
        url.searchParams.delete(key);
      }
    });

    displayFiltersFromURL(url);

    return url;
  }

  // Applies parameters from session variables to URL
  {
    if (typeof filterSession !== 'undefined') {
      var url = applyParametersToURL(filterSession);
      window.history.replaceState({}, document.title, '?' + url.searchParams);
    }
  }
  
  // Parse current parameters from URL
  var order_by = '';
  var searchString = null;
  var selected_codes = [];
  var selected_phenotype_types = [];
  var selected_workingset_types = [];
  var selected_collections = [];
  var selected_tags = [];
  var selected_data_sources = [];
  var start = moment(base_start_date);
  var end = moment(dateValue);
  var rangeName = 'Custom Range';

  var fetchFilterParameters = (location) => {
    var params = new URL(location == undefined ? window.location.href : location);
    params.searchParams.forEach(function (value, key) {
      switch (key) {
        case "data_source_ids":
          selected_data_sources = value.split(',');
          break;
        case "tag_ids":
          selected_tags = value.split(',');
          break;
        case "collection_ids":
          selected_collections = value.split(',');
          break;
        case "codingids":
          selected_codes = value.split(',');
          break;
        case "selected_workingset_types":
          selected_workingset_types = value.split(',')
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
        case "page_size":
          $('#filter_number_option span').text(value);
        default:
          break;
      }

      // Filter null cases
      selected_collections.filter(e => e !== '');
      selected_tags.filter(e => e !== '');
      selected_codes.filter(e => e !== '');
      selected_phenotype_types.filter(e => e !== '');
      selected_workingset_types.filter(e => e !== '');
      selected_data_sources.filter(e => e !== '');

      // Set current input
      $("#basic-form input[name=" + key + "]").val(value);
    });

    if (library == PAGE.WORKINGSET) {
      if (params.searchParams.get('selected_workingset_types') == null) {
        selected_workingset_types = [];
        $("#basic-form input[id=selected_workingset_types]").val('');
        $(".filter_option.types").prop('checked', false);
      }
    }

    if (library == PAGE.PHENOTYPE) {
      if (params.searchParams.get('selected_phenotype_types') == null) {
        selected_phenotype_types = [];
        $("#basic-form input[id=selected_phenotype_types]").val('');
        $(".filter_option.types").prop('checked', false);
      }
    }

    if (library == PAGE.PHENOTYPE || library == PAGE.WORKINGSET) {
      if (params.searchParams.get('data_source_ids') == null) {
        selected_data_sources = [];
        $("#basic-form input[id=data_source_ids]").val('');
        $(".filter_option.datasources").prop('checked', false);
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

    if (params.searchParams.get('owner') == null && params.searchParams.get('author') == null) {
      $("a[href='#collapse-authorship'] .filter_reset_btn").addClass('hide');
    }

    if (params.searchParams.get('codingids') == null) {
      selected_codes = [];
      $("#basic-form input[id=codingids]").val('');
      $(".filter_option.coding").prop('checked', false);
    }

    if (params.searchParams.get('tag_ids') == null) {
      selected_tags = [];
      $("#basic-form input[id=tag_ids]").val('');
      $(".filter_option.tags").prop('checked', false);
    }

    if (params.searchParams.get('collection_ids') == null) {
      selected_collections = [];
      $("#basic-form input[id=collection_ids]").val('');
      $(".filter_option.collection").prop('checked', false);
    }

    if (params.searchParams.get('startdate') == null || params.searchParams.get('enddate') == null) {
      start = moment(base_start_date);
      end = moment(dateValue);
      $("#basic-form input[id=startdate]").val('');
      $("#basic-form input[id=enddate]").val('');
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

  // Open any header with current any selected parameters
  {
    var url = new URL(window.location.href);
    var params = [];

    // Object.keys(dict).length doesn't work in this case so we need to create an array to check len of params
    url.searchParams.forEach((value, key) => {
      params.push([key, value]);
    });

    if (params.length > 0) {
      $('.morphing_caret').each(function () {
        $(this).addClass('closed');
      });
      $('#filter_form .collapse').each((_, elem) => {
        $(elem).removeClass('in');
      });

      for (var i = 0; i < params.length; i++) {
        var param = params[i][0];
        var value = params[i][1];
        if (param == 'tag_collection_ids') {
          // Split tags into collection + tags then resolve collapsed state
          var groups = parseTagsAndCollections(value);
          if (groups.collections) {
            $('#collapse-collection').addClass('in');
            $("a[href='#collapse-collection'] .filter_reset_btn").removeClass('hide');
            $("a[href='#collapse-collection'] .morphing_caret").removeClass('closed');
          }

          if (groups.tags) {
            $('#collapse-tags').addClass('in');
            $("a[href='#collapse-tags'] .filter_reset_btn").removeClass('hide');
            $("a[href='#collapse-tags'] .morphing_caret").removeClass('closed');
          }
          
          continue;
        }

        var header = subheaderMap[param];
        $('#collapse-' + header).addClass('in');
        $("a[href='#collapse-" + header + "'] .filter_reset_btn").removeClass('hide');
        $("a[href='#collapse-" + header + "'] .morphing_caret").removeClass('closed');
      }
    }
  }

  // Handle scroll to top button(s)
  $(document).on('click.filterService', '#scroll_up', (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Animate loading icon on ajax timeout after 0.5s
  var loadingTimeout;
  $(document).on('ajaxStart.filterService', function () {
    loadingTimeout = setTimeout(function () {
      $('#loading_res_spinner').removeClass('hidden');
      $('#result-div').html('');
    }, 500);
  });
  $(document).on('ajaxStop.filterService', function () {
    $('#loading_res_spinner').addClass('hidden');
    clearTimeout(loadingTimeout);
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
      $("#basic-form input[id=order_by]").val($('.order_filter li').first().text());
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

        // Update URL parameters
        var url = applyParametersToURL(values)

        // Apply history to window if page, search query or date is changed, otherwise replace state to avoid unnecessary window hx upd
        if (method.element == 'page' || method.element == 'search' || method.element == 'date') {
          window.history.pushState({}, document.title, '?' + url.searchParams);
        } else {
          window.history.replaceState({}, document.title, '?' + url.searchParams);
        }
      })
      .catch((error) => {
        console.log("[FilterResults]", error);
        if (typeof error === 'object' && typeof error['canceled'] !== 'undefined') {
          return;
        }

        $('.toast_holder').pushToastNotification({
          style: 'error',
          desc: 'An error has occurred. Please try again.'
        });
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
  $(document).on('click.filterService', '.number_filter a', (e) => {
    e.preventDefault();

    var $results = $(e.target).text();
    $('#filter_number_option span').text($results);
    $("#basic-form input[id=page_size]").val($results);
    $("#basic-form").trigger('submit', [{'element': 'page_size'}]);
  });

  // Handle ordering option
  $(document).on('click.filterService', '.order_filter a', (e) => {
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
      if (!isBaseDateRange({"startdate": start, "enddate": end})) {
        $("#basic-form input[id=startdate]").val(start.format('YYYY-MM-DD'));
        $("#basic-form input[id=enddate]").val(end.format('YYYY-MM-DD'));
      } else {
        $("#basic-form input[id=startdate]").val('');
        $("#basic-form input[id=enddate]").val('');
      }
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
    alwaysShowCalendars: true,
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
  
  $(document).on('keypress.filterService', function (e) {
    if (e.keyCode == 13) {
      var $target = $(e.target)
      var $name = $target.attr('name');
      if (!TEXT_QUERIES.includes($target.attr('id'))) {
        return;
      }

      e.preventDefault();

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
  $(document).on('click.filterService', '.btn-paginate', function (e) {
    e.preventDefault();

    var dest = parseInt($(this).attr('value'));
    $("#basic-form input[id=page]").val(dest);
    $("#basic-form").trigger('submit', [{'element': $(this).attr('name')}]);
    window.scrollTo({ top: 0 });
  });

  // Initialise searchbars for long list filter(s)
  var scrollableLists = [];
  var mutateSearchbars = () => {
    for (var i = 0; i < scrollableLists.length; i++) {
      var $element = scrollableLists[i];
      var parent = $element.parent().parent().find('.scrollable_filter_list')[0];
      
      if (!$.isScrollable(parent))
        continue;
      
      if ($.isScrollbarVisible(parent)) {
        $element.parent().removeClass('hide');
      } else {
        $element.parent().addClass('hide');
        $element.val('');
      }
    }
  }

  var resortChildren = (groupName, $holder, $children) => {
    // i.e. checked first, then either sort by asc. order of frequency or desc. order alphabetical
    $children.detach().sort(function (a, b) {
      var v1 = $(a).find('input').first();
      var v2 = $(b).find('input').first();
      if (v1.prop('checked') && !v2.prop('checked')) {
        return -1;
      } else if (v2.prop('checked') && !v1.prop('checked')) {
        return 1;
      } else {
        var ordering = filter_statistics_ordering[groupName];
        if (ordering) {
          // Sort by frequency of occurrence (descending)
          var n1 = ordering[v1.val()];
          var n2 = ordering[v2.val()];
          if (n1 > n2) {
            return -1;
          } else if (n1 < n2) {
            return 1;
          }
        } else {
          // Default to alphabetical order (ascending)
          var n1 = $(a).find('.form-check-label').first().text().trim().toLocaleLowerCase();
          var n2 = $(b).find('.form-check-label').first().text().trim().toLocaleLowerCase();
          if (n1 < n2) {
            return -1;
          } else if (n1 > n2) {
            return 1;
          }
        }
      }

      return 0;
    });
    $holder.append($children);
  }

  // Pulsation animation to highlight newly toggled checkbox after autocomplete
  var pulsateSelected = (item) => {
    $(item).css({opacity: 0});
    $(item).animate({opacity: 1}, 200);
    $(item).animate({opacity: 0}, 200);
    $(item).animate({opacity: 1}, 200);
  }

  $.each(SEARCHBARS[library], (key, group) => {
    var $tags = $('#filter_by_' + group.name + ' .' + group.name);
    var $holder = $tags.first().parent().parent().parent();
    var $children = $holder.children('li');

    // Resort on startup for initialising params
    resortChildren(group.name, $holder, $children);

    // Init typeahead
    $(group.searchbar).autocompleteSearch({
      onQuery: (needle) => {
        if (needle === '') {
          return [];
        }

        var results = FuzzyQuery.Search(group.haystack, needle, FuzzyQuery.Results.SORT, FuzzyQuery.Transformers.IgnoreCase);
        results.sort((a, b) => {
          if (a.score === b.score) {
            return 0;
          } else if (a.score > b.score) {
            return 1;
          } else if (a.score < b.score) {
            return -1;
          }
        });
        results = results.map((e) => {
          var item = group.reference.find(x => x.name.toLocaleLowerCase() === e.item.toLocaleLowerCase());
          return item.name;
        });

        return results;
      },
      onFocusLost: () => {
        resortChildren(group.name, $holder, $children);
      },
      onSelected: (val) => {
        resortChildren(group.name, $holder, $children);
        
        var child = $holder.children('li').find('.form-check-label').filter(function () {
          return $(this).text().trim().toLocaleLowerCase() == val.toLocaleLowerCase();
        })[0];

        if (child) {
          var item = child.parentNode.parentNode;
          var checkbox = $(child.parentNode).find('input');
          var scrollHeight = SHOULD_TOGGLE_SEARCH ? $holder.scrollTop() - $holder.offset().top : $holder.scrollTop() - $holder.offset().top + $(item).offset().top;

          if (SHOULD_TOGGLE_SEARCH) {
            checkbox.prop('checked', !(checkbox.prop('checked')));
            checkbox.trigger('change');
          }

          $holder.animate(
            { scrollTop: scrollHeight },
            {
              duration: 500,
              complete: () => {
                pulsateSelected(item);
              }
            }
          );
        }
      }
    });
    scrollableLists.push($(group.searchbar));
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
          setTimeout(mutateSearchbars, 100);
        });
        $(obj).on('hide.bs.collapse', function () {
          $(icons).toggleClass('closed');
        });
      }
    }
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

    selected_tags = []
    $("input:checkbox[name=tag_id]:checked").each(function(){
      selected_tags.push(parseInt($(this).val()));
    });
    
    
    $("#basic-form input[id=page]").val(1);

    if (library == PAGE.WORKINGSET) {
      selected_workingset_types = [];
      $("input:checkbox[name=type_name]:checked").each(function(){
        selected_workingset_types.push($(this).val());
      });

      $("#basic-form input[id=selected_workingset_types]").val(selected_workingset_types.join(','));
    }

    if (library == PAGE.PHENOTYPE) {
      selected_phenotype_types = [];
      $("input:checkbox[name=type_name]:checked").each(function(){
        selected_phenotype_types.push($(this).val());
      });

      $("#basic-form input[id=selected_phenotype_types]").val(selected_phenotype_types.join(','));
    }

    if (library == PAGE.PHENOTYPE || library == PAGE.WORKINGSET) {
      selected_data_sources = [];
      $("input:checkbox[name=source_id]:checked").each(function() {
        selected_data_sources.push(parseInt($(this).val()));
      });
      $("#basic-form input[id=data_source_ids]").val(selected_data_sources.join(','));
    }

    $("#basic-form input[id=collection_ids]").val(selected_collections);
    $("#basic-form input[id=tag_ids]").val(selected_tags);
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

  // Apply responsive style @ media query
  var $result_page = $('#result-div');
  var conditionallyHidePadding = (win) => {
    if (win.width() > FILTER_HIDE_WIDTH) {
      $(".filter_modal_button").parent().addClass("hide");
    } else {
      $(".filter_modal_button").parent().removeClass("hide");
    }
  }

  var resizeResultPage = (win) => {
    // Mutate the visibility of searchbars by scrollable size
    mutateSearchbars();

    // Resize the result div
    if (win.width() < FILTER_HIDE_WIDTH) {
      $result_page.removeClass('col-sm-10');
      $result_page.addClass('col-sm-12');
    } else {
      $result_page.addClass('col-sm-10');
      $result_page.removeClass('col-sm-12');
    }
    
    // Hide extra padding that's only visible for authenticated and/or mobile user(s)
    if (library == PAGE.PHENOTYPE) {
      conditionallyHidePadding(win);
    } else if (library == PAGE.CONCEPT) {
      if ($(".filter_modal_button").parent().children().length <= 1) {
        conditionallyHidePadding(win);
      }
    }

    // Pad navbar
    var $nav = $("#nav_bar_main .container");
    var offset = ($nav.height() / 2) - 25;
    $(".bg-search").css("padding-top", offset);
  }

  $(window).on('resize', function() {
    var win = $(this);
    resizeResultPage(win);
  });
  resizeResultPage($(window));

  // Filter modal button for mobile devices
  var $filter_panel = $('#filter_panel_group');
  var $filter_modal = $('#filter-modal');
  $filter_modal.on('shown.bs.modal', (e) => {
    $filter_panel.find('#filter_form').first().appendTo($filter_modal.find('.modal-body').first());
    $filter_panel.find('.filter_buttons').first().appendTo($filter_modal.find('.modal-footer').first());

    mutateSearchbars();
  });
  $filter_modal.on('hide.bs.modal', (e) => {
    $filter_modal.find('#filter_form').first().appendTo($filter_panel);
    $filter_modal.find('.filter_buttons').first().appendTo($filter_panel);
  });

  // Conditional sticky filter component
  var $container = $('.filter_container');
  var resetComponent = () => {
    if (!$container.data("isSticky"))
      return;

    $container.data("isSticky", false);
    $container.css({
      "position": "relative",
      "height": "",
      "top": "",
    });
  }

  var animateIntoFrame = (offset, resolve, reject) => {
    if (!$container.data("isSticky")) {
      reject();
      return;
    }

    var height = $(window).scrollTop();
    var position = $container.position().top;
    var extents = $container.offset().top;
    var pageSize = $("#page_extents").position().top + $("#page_extents").height();
    if ((position >= height) || ((position + extents) >= pageSize)) {
      resolve();
      return;
    }
    
    offset += STICKY_SPEED;
    $container.css("top", offset);

    setTimeout(function () {
      animateIntoFrame(offset, resolve, reject);
    }, STICKY_INTERVAL);
  }

  var stickifyComponent = () => {
    $container.data("isSticky", true);
    
    return new Promise((resolve, reject) => {
      var start = $container.position().top + $container.height() / 2;
      animateIntoFrame(start, resolve, reject);
    })
    .then(() => {
      $container.css({
        "position": "sticky",
        "height": "min-content",
        "top": "60px",
      });
    })
    .catch((ex) => {
      console.log("[Stickify]", ex);
    });
  }
  
  var mutateStickyComponent = () => {
    if ($(".filter_modal_button a").css("visibility") !== "visible") {
      var extent = $container.parent().position().top + $container.height() - STICKY_OFFSET;
      var scroll = $(window).scrollTop();

      if (scroll >= extent) {
        if ($container.data("isSticky"))
          return;
        
        // Animate the component into position until we can make it sticky (avoids jarring jump)
        stickifyComponent();
      } else {
        // Reset since we're back to the normal filter component position
        resetComponent();
      }
    } else {
      // Small size resolution e.g. mobile, so we reset the component
      resetComponent();
    }
  }

  // Mutate the sticky component on element resize & window scrolling
  var resizeObserver = new ResizeObserver(mutateStickyComponent).observe($container[0]);
  $(document).scroll(function (e) {
    mutateStickyComponent();
  });

  // Individual filter resets
  $('.filter_reset_btn').on('click', function (e) {
    // Stops clickthrough propagation to parent element
    e.stopImmediatePropagation();
    e.preventDefault();
    
    // Update a fake URl then pass to submission handler
    var $header = $(this).parent().parent().parent();
    var type = $header.attr('href').replace('#collapse-', '');
    var mapped = elementMap[type];
    if (mapped !== 'undefined') {
      var url = new URL(window.location.href);
      if (type === 'tags' || type === 'collection') {
        var selected = url.searchParams.get(mapped[0]);
        if (selected != null) {
          selected = parseTagsAndCollections(selected);
          selected = type == "tags" ? selected.collections : selected.tags;

          if (type == "tags") {
            $(".filter_option.tags").each((i, v) => {
              $(v).prop("checked", false);
            });
          } else {
            $(".filter_option.collection").each((i, v) => {
              $(v).prop("checked", false);
            });
          }

          var q = type == 'tags' ? 'tag_ids' : 'collection_ids';
          if (selected) {
            url.searchParams.set(q, selected.join(','));
          } else {
            url.searchParams.delete(q);
          }
        } else {
          url.searchParams.delete(mapped[0]);
        }
      } else {
        for (var i = 0; i < mapped.length; i++) {
          url.searchParams.delete(mapped[i]);
        }
      }

      fetchFilterParameters(url);
      $("#basic-form").trigger('submit', [{'element': 'search'}]);
    }
  });
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