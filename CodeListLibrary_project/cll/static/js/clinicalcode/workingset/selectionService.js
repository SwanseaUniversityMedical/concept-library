var SelectionService = function (element, methods, previouslySelected = []) {
  /*************************************
   *                                   *
   *            Private defs           *
   *                                   *
   *************************************/
  var MODAL_SETTINGS = {
    // If static, modal won't close when clicking outside the bounds of the modal
    backdrop: 'static',
    // If false, the modal won't listen to key presses to trigger events e.g. KEYCODE.ESC will not close the window
    keyboard: false,
  }

  var DEFAULT_VALUES = {
    page: '1',
    page_size: '20',
    search: '',
    tag_ids: '',
    collection_ids: '',
    coding_ids: '',
    selected_phenotype_types: '',
    data_source_ids: '',
    startdate: '',
    enddate: '',
    owner: '',
    author: '',
  }

  var MAPPED_TYPE = {
    type: 'selected_phenotype_types',
    collection: 'collection_ids',
    tags: 'tag_ids',
    coding: 'coding_ids',
    datasources: 'data_source_ids',
    date: undefined,
    authorship: undefined,
  }

  var SEARCHBARS = {
    tags: {
      name: 'tags',
      searchbar: '#tag_searchbar',
      haystack: null,
      reference: null
    },
    collections: {
      name: 'collection',
      searchbar: '#collection_searchbar',
      haystack: null,
      reference: null
    },
    coding: {
      name: 'coding',
      searchbar: '#coding_searchbar',
      haystack: null,
      reference: null
    },
    types: {
      name: 'types',
      searchbar: '#type_searchbar',
      haystack: null,
      reference: null
    },
    datasources: {
      name: 'datasources',
      searchbar: '#datasources_searchbar',
      haystack: null,
      reference: null
    },
  }

  var MAPPED_HEADER = {
    type_name: {
      href: '#collapse-type',
      data: 'selected_phenotype_types',
    },
    collection_id: {
      href: '#collapse-collection',
      data: 'collection_ids',
    },
    tag_id: {
      href: '#collapse-tags',
      data: 'tag_ids',
    },
    coding_id: {
      href: '#collapse-coding',
      data: 'coding_ids',
    },
    source_id: {
      href: '#collapse-datasources',
      data: 'data_source_ids',
    },
    daterange: {
      href: '#collapse-date',
      data: null,
    },
    author: {
      href: '#collapse-authorship',
      data: 'author',
    },
    owner: {
      href: '#collapse-authorship',
      data: 'owner',
    },
  }

  var MAPPED_DATA = {
    coding_data: 'filter_by_coding',
    collection_data: 'filter_by_collection',
    datasource_data: 'filter_by_datasources',
    phenotype_data: 'filter_by_types',
    tag_data: 'filter_by_tags',
  }

  var MAPPED_DATA_TYPE = {
    coding_id: 'coding_ids',
    collection_id: 'collection_ids',
    source_id: 'data_source_ids',
    type_name: 'selected_phenotype_types',
    tag_id: 'tag_ids',
  }

  var MAPPED_ITEM_NAME = {
    coding_data: {
      item: 'coding',
      name: 'coding_id',
      src: 'coding',
    },
    collection_data: {
      item: 'collection',
      name: 'collection_id',
      src: 'collections',
    },
    datasource_data: {
      item: 'datasources',
      name: 'source_id',
      src: 'datasources',
    },
    phenotype_data: {
      item: 'types',
      name: 'type_name',
      src: 'types',
    },
    tag_data: {
      item: 'tags',
      name: 'tag_id',
      src: 'tags',
    },
  }

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
  

  /*************************************
   *                                   *
   *            Public props           *
   *                                   *
   *************************************/
  this.data = undefined;
  this.filter_order = undefined;
  this.element = element[0];
  this.selected = previouslySelected;
  this.onImport = methods.onImport || (() => { });
  this.onClose = methods.onClose || (() => { });
  this.modal = null;
  this.filters = Object.assign({}, DEFAULT_VALUES);
  this.clearOnClose = methods.clearSelectedOnClose || false;
  this.clearOnImport = methods.clearSelectedOnImport || false;


  /*************************************
   *                                   *
   *           Private methods         *
   *                                   *
   *************************************/

  /* Push updates to selected components tab */
  var updateSelectedConcepts = (modal) => {
    // Update selected tab component
    var container = modal.find('#ws-active-selection');
    container.html(createNullComponent());
    
    for (var index in this.selected) {
      var elem = this.selected[index];
      createConceptComponent(elem)
        .appendTo(container)
        .find('button')
        .on('click', (e) => {
          e.preventDefault();

          var data = $(e.target).parent().find('input[name="ws-concept-data"]').val().split(':');
          var selected = this.selected.find(e => e.concept.id == data[0] && e.concept.version == data[1]);
          if (selected) {
            var index = this.selected.indexOf(selected);
            this.selected.splice(index, 1);
            updateSelectedConcepts(modal);
            toggleConcepts(modal);
          }
        });
    }

    // Update bubble counter
    var $bubble = modal.find('.ws-notify-bubble');
    var $nosel = modal.find('#ws-no-selection');
    if (this.selected.length > 0) {
      $bubble.removeClass('hide');
      $nosel.addClass('hide');
    } else {
      $bubble.addClass('hide');
      $nosel.removeClass('hide');
    }
    $bubble.text(this.selected.length.toString());
  }

  /* Handles interaction with concept checkbox */
  var toggleConcepts = (modal) => {
    var $concepts = modal.find('.ws-concept-option');
    $concepts.each((i, elem) => {
      var data = $(elem).val().split(':');
      var selected = this.selected.find(e => e.concept.id == data[0] && e.concept.version == data[1]);
      if (typeof selected == 'undefined') {
        $(elem).prop('checked', false);
        return;
      }
      
      $(elem).prop('checked', true);
    });
  }

  var handleConcepts = (modal) => {
    updateSelectedConcepts(modal);
    toggleConcepts(modal);

    var $concepts = modal.find('.ws-concept-option');
    $concepts.change((e) => {
      var elem = $(e.target);
      var data = $(elem).val().split(':');
      var selected = this.selected.find(e => e.concept.id == data[0] && e.concept.version == data[1]);
      if (selected) {
        // Pop
        var index = this.selected.indexOf(selected);
        this.selected.splice(index, 1);
      } else {
        // Push
        var name = elem.parent().find('input[name="ws-concept-name"]').val();
        var code = elem.parent().find('input[name="ws-concept-coding"]').val();
        var pheno = elem.parent().find('input[name="ws-phenotype-element"]').val().split(':');
        this.selected.push({
          concept: {
            name: name,
            coding: code,
            id: data[0],
            version: data[1],
          },
          phenotype: {
            name: pheno[0],
            id: pheno[1],
            version: pheno[2]
          }
        });
      }

      updateSelectedConcepts(modal);
    });
  }

  /* Update subheader's filter reset buttons */
  var updateSubheader = (name, value) => {
    var obj = MAPPED_HEADER[name];
    if (typeof obj === 'undefined')
      return;
    
    switch (name) {
      case "daterange": {
        if (isBaseDateRange(value)) {
          this.modal.find('a[href="' + obj.href + '"] .filter_reset_btn').addClass("hide");
        } else {
          this.modal.find('a[href="' + obj.href + '"] .filter_reset_btn').removeClass("hide");
        }
        break;
      }
      default: {
        if (value !== DEFAULT_VALUES[obj.data]) {
          this.modal.find('a[href="' + obj.href + '"] .filter_reset_btn').removeClass("hide");
        } else {
          this.modal.find('a[href="' + obj.href + '"] .filter_reset_btn').addClass("hide");
        }

        break;
      }
    }
  }

  /* Det. whether date range differs from predef. */
  var isBaseDateRange = (params) => {
    if (params['startdate'] === null && params['enddate'] === null) {
      return true;
    }

    var startdate = params['startdate'];
    var enddate = params['enddate'];
    return (startdate == base_start_date.format('YYYY-MM-DD') && enddate == dateValue.format('YYYY-MM-DD'));
  }

  /* Transform from lowercase to Title Case */
  var transformTitleCase = (str) => {
    return str.replace(/(^|\s)\S/g, function (t) {
      return t.toUpperCase();
    });
  }

  /* Generate list element(s) for filter(s) */
  var generateListElement = (mapped, name, value) => {
    return $(`
    <li class="checkbox">
      <label>
        <input class="form-check-input filter_option ` + mapped.item +`" type="checkbox" name="` + mapped.name + `" value="` + value + `">
        <span class="form-check-label">
          ` + (name.toLocaleLowerCase() == name ? transformTitleCase(name) : name) + `
        </span>
      </label>
    </li>
    `);
  }

  /* Resort children for typeahead searchbars */
  var resortChildren = (groupName, $holder, $children) => {
    // i.e. checked first, then either sort by asc. order of frequency or desc. order alphabetical
    $children.detach().sort((a, b) => {
      var v1 = $(a).find('input').first();
      var v2 = $(b).find('input').first();
      if (v1.prop('checked') && !v2.prop('checked')) {
        return -1;
      } else if (v2.prop('checked') && !v1.prop('checked')) {
        return 1;
      } else {
        var ordering = this.filter_order[groupName];
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

  /* Pulsation animation to highlight newly toggled checkbox after autocomplete */
  var pulsateSelected = (item) => {
    $(item).css({opacity: 0});
    $(item).animate({opacity: 1}, 200);
    $(item).animate({opacity: 0}, 200);
    $(item).animate({opacity: 1}, 200);
  }

  /* Mutate scroll visibility by list size(s) */
  var mutateSearchbars = scrollableLists => {
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

  /* Generate typeahead searchbars */
  var generateSearchbars = (modal) => {
    var scrollableLists = [];
    $.each(SEARCHBARS, (key, group) => {
      var $tags = modal.find('#filter_by_' + group.name + ' .' + group.name);
      var $holder = $tags.first().parent().parent().parent();
      var $children = $holder.children('li');

      // Resort on startup for initialising params
      resortChildren(group.name, $holder, $children);

      // Init typeahead
      modal.find(group.searchbar).autocompleteSearch({
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
            var scrollHeight = $holder.scrollTop() - $holder.offset().top;

            checkbox.prop('checked', !(checkbox.prop('checked')));
            checkbox.trigger('change');

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
      scrollableLists.push(modal.find(group.searchbar));
    });

    return scrollableLists;
  }

  /* Instantiate & handle filter objects */
  var handleFilters = (modal) => {
    // Individual filter reset button(s)
    modal.find('.filter_reset_btn').on('click', (e) => {
      e.stopImmediatePropagation();
      e.preventDefault();

      var target = $(e.target).parent().parent().parent().parent().attr('href').replace('#collapse-', '');
      var map = MAPPED_TYPE[target];
      if (typeof map !== 'undefined') {
        this.filters[map] = DEFAULT_VALUES[map];

        // Reset checkbox
        modal.find(".filter_option." + (target == 'type' ? 'types' : target)).each((i, v) => {
          $(v).prop("checked", false);
        });

        return fetchResults(this.filters).finally(() => {
          modal.find('a[href="#collapse-' + target + '"] .filter_reset_btn').addClass("hide");
        });
      }

      switch (target) {
        case "date": {
          this.filters.startdate = '';
          this.filters.enddate = '';

          // Reset date range
          var $picker = modal.find('#filter_date').data('daterangepicker');
          if ($picker !== undefined) {
            $picker.startDate = moment(base_start_date);
            $picker.endDate = moment(dateValue);
            $picker.calculateChosenLabel();
            modal.find('#filter_date span').html('All');
          }
          break;
        }
        case "authorship": {
          this.filters.owner = this.filters.author = '';

          // Reset values
          modal.find('#author_text').val('');
          modal.find('#owner_text').val('');
          break;
        }
        default:
          break;
      }

      return fetchResults(this.filters).finally(() => {
        modal.find('a[href="#collapse-' + target + '"] .filter_reset_btn').addClass("hide");
      });
    });

    // Generate filter elements & set up searchbars
    $.each(this.data, (key, data) => {
      var list = modal.find('#' + MAPPED_DATA[key] + ' .scrollable_filter_list');

      // Elements
      var map = MAPPED_ITEM_NAME[key];
      $.each(data, (i, e) => {
        var $elem = generateListElement(map, e.name, e.id)
        $elem.appendTo(list);
      });

      // Searchbar data
      SEARCHBARS[map.src].haystack = data.map(e => e.name);
      SEARCHBARS[map.src].reference = data;
    });

    // Handle checkbox logic
    modal.find('.filter_option').change((e) => {
      var selected = [];
      var $element = $(e.target);
      modal.find('input:checkbox[name=' + $element.attr('name') + ']:checked').each((i, v) => {
        selected.push($(v).val());
      });
      selected = selected.join(',');
      this.filters[MAPPED_DATA_TYPE[$element.attr('name')]] = selected;

      // Trigger
      fetchResults(this.filters);
      updateSubheader($element.attr('name'), selected);
    });

    // Handle internal filter searchbar(s)
    var scrollableLists = generateSearchbars(modal);

    // Handle search & authorship
    $.each(['ws_searchbar', 'author_text', 'owner_text'], (i, selector) => {
      modal.find('#' + selector).on('keypress', (e) => {
        if (e.keyCode != 13)
          return;
        
        e.preventDefault();

        var $target = $(e.target);
        var $name = $target.attr('name');
        switch ($name) {
          case "author":
            this.filters.author = $target.val();
            break;
          case "owner":
            this.filters.owner = $target.val();
            break;
          case "search":
            this.filters.search = $target.val();
          default:
            break;
        }
        
        // Trigger
        fetchResults(this.filters);
        updateSubheader($name, $target.val());
      });
    });
    
    // Handle collapsible states
    modal.find('.collapse').each(function (i, obj) {
      var anchor = modal.find('a[href^="#' + this.id + '"]')[0];
      if (typeof anchor !== 'undefined') {
        var icons = $(anchor).find('.morphing_caret')[0];
        if (typeof icons !== 'undefined') {
          $(obj).on('show.bs.collapse', function () {
            $(icons).toggleClass('closed');
            setTimeout(() => {
              mutateSearchbars(scrollableLists);
            }, 100);
          });
          $(obj).on('hide.bs.collapse', function () {
            $(icons).toggleClass('closed');
          });
        }
      }
    });

    // Handle daterangepicker
    var initialisedDate = false;
    var setDateRange = (start, end, period) => {
      switch (period) {
        case "Custom Range": {
          modal.find('#filter_date span').html(start.format('DD MMM YY') + ' - ' + end.format('DD MMM YY'));
          break;
        }
        default: {
          modal.find('#filter_date span').html(period);
          break;
        }
      }

      if (initialisedDate) {
        this.filters.page = 1
        if (!isBaseDateRange({"startdate": start, "enddate": end})) {
          this.filters.startdate = start.format('YYYY-MM-DD');
          this.filters.enddate = end.format('YYYY-MM-DD');
        } else {
          this.filters.startdate = this.filters.enddate = '';
        }
        
        // Trigger
        fetchResults(this.filters);
        updateSubheader('daterange', {"startdate": start, "enddate": end});
      } else {
        initialisedDate = true;
      }
    }

    modal.find('#filter_date').daterangepicker({
      startDate: moment(base_start_date),
      endDate: moment(dateValue),
      drops: 'auto',
      showDropdowns: true,
      alwaysShowCalendars: true,
      maxYear: dateValue.year(),
      ranges: dateRanges,
    }, setDateRange);

    setDateRange(moment(base_start_date), moment(dateValue), 'All');

    // Handle resize
    new ResizeObserver(() => {
      mutateSearchbars(scrollableLists);
    }).observe(modal[0]);
  }

  /* Handle events related to the modal */
  var handleEvents = (modal) => {
    // Callback for importing concepts
    modal.find('#import-concepts').on('click', (e) => {
      var currentSelection = this.selected;
      modal.modal('hide');

      if (this.clearOnImport) {
        this.selected = [];
      }

      this.onImport(this, currentSelection);
    });

    // Callback for clearing all selected concept(s)
    modal.find('#clear-all-concepts').on('click', (e) => {
      this.selected = [];
      updateSelectedConcepts(modal);
      toggleConcepts(modal);
    });

    // Callback for changing tabs
    modal.find('a[data-toggle="tab"]').on('shown.bs.tab', (e) => {
      var target = $(e.target).attr('id');
      switch (target) {
        case "ws-add-concepts":
          modal.find('#clear-all-concepts').addClass('hide');
          break;
        case "ws-selected-concepts":
          modal.find('#clear-all-concepts').removeClass('hide');
          break;
      }
    });

    // Callback for modal closure
    modal.on('hidden.bs.modal', () => {
      var currentSelection = this.selected;
      this.modal.remove();
      this.modal = null;
      this.filters = Object.assign({}, DEFAULT_VALUES);

      if (this.clearOnClose) {
        this.selected = [];
      }

      if (this.selected.length > 0) {
        this.onClose(this, currentSelection);
      }
    });
  }

  /* Handle events related to pagination */
  var handlePagination = (controls) => {
    // Handle results per page & pagination elements
    controls.find('.btn-paginate').on('click', (e) => {
      e.preventDefault();

      var target = $(e.target);
      var dest = parseInt(target.attr('value'));
      this.filters.page = dest;
      
      // Trigger
      fetchResults(this.filters);

      // Scroll to top of internal window
      this.modal.find('#selection-results').animate(
        { scrollTop: 0 },
        { duration: 500 },
      );
    });

    // Handle page size
    controls.find('.number_filter a').on('click', (e) => {
      e.preventDefault();

      var $results = $(e.target).text();
      controls.find('#filter_number_option span').text($results);
      this.filters.page_size = $results;

      // Trigger
      fetchResults(this.filters);
    });
  }

  /* Create HTML component(s) */
  var createConceptComponent = (elem) => {
    var id    = elem.concept.id,
      version = elem.concept.version,
      name    = elem.concept.name,
      coding  = elem.concept.coding;
    
    return $(`
    <div class="cl-card ws-no-hover ws-md-padding">
      <button class="btn btn-cl-danger ws-trash" id="ws-remove-concept">
        <i class="fa fa-trash ws-disabled-link" aria-hidden="true"></i>
      </button>
      <label>
        <input type="hidden" name="ws-concept-data" value="` + id + `:` + version + `">
        <span>
          <i class="ws-id-title">C` + id + `/` + version + `:</i>
          &nbsp;
          ` + name + `
          &nbsp;
          ` + coding + `
          &nbsp;
        </span>
      </label>
    </div>
    `);
  }

  var createNullComponent = () => {
    return `
    <p class="ws-none-selected" id="ws-no-selection">You have not selected any Concepts yet.</p>
    `
  }

  var createSelectionComponent = () => {
    return `
    <div class="row">
      <div class="col-xs-12 ws-selected-container">
        <div class="ws-group ws-lg-margin">
          <h1>Selected:</h1>
          <div class="well ws-well-background ws-selected-box" id="ws-active-selection">` + 
            createNullComponent()
          + `</div>
        </div>
      </div>
    </div>
    `
  }

  var createFilterBox = () => {
    return `
    <!-- Type -->
    <a data-toggle="collapse" href="#collapse-type" aria-expanded="true" aria-controls="collapse-type" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Type
          </div>
          <span class="fa fa-angle-up morphing_caret" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    
    <div class="filter-content collapse in" id="collapse-type">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_types">
        <div class="query_filter">
          <input type="text" autocomplete="false"  class="form-control" id="type_searchbar" placeholder="Search...">
        </div>
        <hr class="hr_filter">
        <ul class="scrollable_filter_list">
          <p class="hide" id="filter_no_result" style="text-align: center;">No results found.</p>
        </ul>
      </div>
    </div>

    <!-- Collections tags -->
    <a data-toggle="collapse" href="#collapse-collection" aria-expanded="true" aria-controls="collapse-collection" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Collection
          </div>
          <span class="fa fa-angle-up morphing_caret closed" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    
    <div class="filter-content collapse" id="collapse-collection">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_collection">
        <div class="query_filter">
          <input type="text" autocomplete="false"  class="form-control" id="collection_searchbar" placeholder="Search...">
        </div>
        <hr class="hr_filter">
        <ul class="scrollable_filter_list">
          <p class="hide" id="filter_no_result" style="text-align: center;">No results found.</p>
          
        </ul>
      </div>
    </div>
      
    <!-- Tags -->
    <a data-toggle="collapse" href="#collapse-tags" aria-expanded="true" aria-controls="collapse-tags" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Tags
          </div>
          <span class="fa fa-angle-up morphing_caret closed" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    
    <div class="filter-content collapse" id="collapse-tags">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_tags">
        <div class="query_filter">
          <input type="text" autocomplete="false"  class="form-control" id="tag_searchbar" placeholder="Search...">
        </div>
        <hr class="hr_filter">
        <ul class="scrollable_filter_list">
          <p class="hide" id="filter_no_result" style="text-align: center;">No results found.</p>
        </ul>
      </div>
    </div>

    <!-- Coding system -->
    <a data-toggle="collapse" href="#collapse-coding" aria-expanded="true" aria-controls="collapse-type" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer text-left panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Coding System
          </div>
          <span class="fa fa-angle-up morphing_caret closed" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    <div class="filter-content collapse" id="collapse-coding">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_coding">
        <div class="query_filter">
          <input type="text" autocomplete="false"  class="form-control" id="coding_searchbar" placeholder="Search...">
        </div>
        <hr class="hr_filter">
        <ul class="scrollable_filter_list">
          <p class="hide" id="filter_no_result" style="text-align: center;">No results found.</p>
        </ul>
      </div>
    </div>

    <!-- Data sources -->
    <a data-toggle="collapse" href="#collapse-datasources" aria-expanded="true" aria-controls="collapse-datasources" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Data Source
          </div>
          <span class="fa fa-angle-up morphing_caret closed" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    
    <div class="filter-content collapse" id="collapse-datasources">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_datasources">
        <div class="query_filter">
          <input type="text" autocomplete="false"  class="form-control" id="datasources_searchbar" placeholder="Search...">
        </div>
        <hr class="hr_filter">
        <ul class="scrollable_filter_list">
          <p class="hide" id="filter_no_result" style="text-align: center;">No results found.</p>
        </ul>
      </div>
    </div>

    <!-- Date tags -->
    <a data-toggle="collapse" href="#collapse-date" aria-expanded="true" aria-controls="collapse-date" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Date
          </div>
          <span class="fa fa-angle-up morphing_caret closed" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    <div class="filter-content collapse" id="collapse-date">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_date">
        <div id="filter_date" style="background: #fff; cursor: pointer; padding: 5px 10px; border: 1px solid #ccc; border-radius: 5px; width: 100%; text-decoration: inherit !important;">
          <i class="fa fa-calendar"></i>&nbsp;
          <span></span>
          <i class="fa fa-caret-down" style="display: inline; float: right; margin-top: 2px;"></i>
        </div>
      </div>
    </div>

    <!-- Authorship tags -->
    <a data-toggle="collapse" href="#collapse-authorship" aria-expanded="true" aria-controls="collapse-authorship" style="color: inherit; text-decoration: inherit;">
      <div class="panel-footer panel_transparent">
        <div class="filter_title_content filter_overflow">
          <span class="filter_reset_btn hide">
            <i class="fa fa-window-close"></i>
          </span>
          <div class="filter_title">
            Authorship
          </div>
          <span class="fa fa-angle-up morphing_caret closed" aria-hidden="true"></span>
        </div>
      </div>
    </a>
    
    <div class="filter-content collapse" id="collapse-authorship">
      <div class="panel-body filter_checkbox" style="padding: 0;" id="filter_by_authorship">
        <label for="author" style="font-weight: normal;">Authored by: <i class="help-block-no-break" style="font-size: 10px;">(free text)</i></label>
        <input class="form-control" type="text" name="author" id="author_text" value="">
        <label for="owner" style="font-weight: normal;">Owned by: <i class="help-block-no-break" style="font-size: 10px;">(full user name)</i></label>
        <input class="form-control" type="text" name="owner" id="owner_text" value="">
      </div>
    </div>
    `
  }

  var createSelectionModal = () => {
    return $(`
    <div class="modal fade" id="selection-modal" tabindex="-1" role="dialog" aria-labelledby="selection-modal" aria-hidden="true">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header ws-header">
            <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
            <ul class="nav nav-tabs ws-nav" role="tablist">
              <li role="presentation" class="active">
                <a href="#ws-add-concept-tab" id="ws-add-concepts" aria-controls="add-concept" role="tab" data-toggle="tab">
                  Add Concepts
                </a>
              </li>
              <li role="presentation">
                <a href="#ws-selected-concept-tab" id="ws-selected-concepts" aria-controls="selected-concept" role="tab" data-toggle="tab">
                  Selected Concepts
                </a>
                <span class="ws-notify-bubble hide">0</span>
              </li>
            </ul>
          </div>
          <div class="modal-body ws-content">
            <div class="tab-content ws-tab-content">
              <div role="tabpanel" class="tab-pane ws-tab-panel active" id="ws-add-concept-tab">
                <div class="row">
                  <div class="col-xs-4 ws-sidebar ws-border" id="selection-filters">
                    <div class="ws-searchbar ws-group">
                      <h1>Search</h1>
                      <div class="ws-box">
                        <input type="text" class="form-control" id="ws_searchbar" placeholder="Search..." name="search">
                      </div>
                    </div>
                    <div class="ws-filters ws-group">
                      <h1>Filters</h1>
                      <div class="ws-box ws-filter-box well ws-well-background">` + 
                        createFilterBox()
                      + `</div>
                    </div>
                  </div>
                  <div class="col-xs-8 ws-result-container">
                    <div class="ws-page-control" id="static-pagination-controller"></div>
                    <div class="ws-results" id="selection-results">

                    </div>
                  </div>
                </div>
              </div>
              <div role="tabpanel" class="tab-pane ws-tab-panel" id="ws-selected-concept-tab">` + 
                createSelectionComponent()
              + `</div>
            </div>
          </div>
          <div class="modal-footer">
            <a class="btn btn-outline-primary btn-cl btn-cl-danger hide" id="clear-all-concepts">
              Clear Selected
            </a>
            <a class="btn btn-outline-primary btn-cl btn-cl-secondary" id="import-concepts">
              Apply changes
            </a>
          </div>
        </div>
      </div>
    </div>`)
  }
  
  /* AJAX request handling */
  var cancellablePromise = promise => {    
    var rejected;
    var wrapped = new Promise((resolve, reject) => {
      rejected = reject;
      Promise.resolve(promise).then(resolve).catch(reject);
    });
  
    wrapped.cancel = () => {
      rejected({canceled: true});
    }
  
    return wrapped;
  }
  
  var currentQuery;
  var postQuery = (values) => {
    if (currentQuery) {
      currentQuery.cancel();
    }
  
    var getResults = new Promise((resolve, reject) => {
      $.ajax({
        url: '/workingsets/select-concepts/',
        type: 'GET',
        data: Object.assign(values, {method: 1}),
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

  var sanitiseFilters = (values) => {
    values = values || { };

    var query = { };
    for (var property in values) {
      if (DEFAULT_VALUES[property] !== values[property]) {
        query[property] = values[property];
      }
    }

    return query;
  }

  var fetchResults = (values) => {
    values = sanitiseFilters(values);

    return postQuery(values)
      .then((data) => {
        this.modal.find('#selection-results').html(data);

        // Parse filter order
        var $data = this.modal.find('#ws-hidden-order');
        if (typeof $data[0] !== 'undefined') {
          this.filter_order = JSON.parse($data.val());
        }

        // Parse filter data
        var $data = this.modal.find('#ws-hidden-data');
        if (typeof $data[0] !== 'undefined') {
          this.data = JSON.parse($data.val());
        }

        // Parse pagination
        var $pagination = this.modal.find('#pagination-controller');
        if (typeof $pagination[0] !== 'undefined') {
          var $controls = this.modal.find('#static-pagination-controller');
          $controls.html($pagination.html());
          $pagination.remove();

          handlePagination($controls);
        }

        // Pass ctx to concept handle
        handleConcepts(this.modal);
      })
      .catch((error) => {
        if (typeof error === 'object' && typeof error['canceled'] !== 'undefined') {
          return;
        }

        console.warn(error);
      })
  }


  /*************************************
   *                                   *
   *             Initialise            *
   *                                   *
   *************************************/
  $(this.element).on('click', (e) => {
    e.preventDefault();

    // Initialise modal
    this.modal = createSelectionModal();

    // Initialise state
    fetchResults(this.filters)
      .finally(() => {
        // Initialise UIx
        handleFilters(this.modal);
        handleEvents(this.modal);

        // Pop modal
        this.modal.prependTo($('body'));
        this.modal.modal(MODAL_SETTINGS, 'show');
      })
  });
}


/*************************************
 *                                   *
 *           Public methods          *
 *                                   *
 *************************************/
SelectionService.prototype = {
  constructor: SelectionService,
  destroy: function () {
    // Delete SelectionService & clean up
    this.modal.remove();
    this.selected = null;
    this.modal = null;
    this.filters = null;
    $(this.element).data('SelectionService', undefined);
    delete this;
  },
  getSelected: function () {
    return this.selected;
  },
  getModal: function () {
    return this.modal;
  }
};


/*************************************
 *                                   *
 *           jQuery plugin           *
 *                                   *
 *************************************/
$.fn.createSelection = function (methods, previouslySelected) {
  methods = methods || { };

  var service = new SelectionService(this, methods, previouslySelected);
  $(this).data('SelectionService', service);

  return this;
}
