var TagService = function (element, groups, methods, filters) {
  this.element = element[0];
  this.groups = groups;
  this.active = {};
  this.onRemove = methods.onRemove || (() => { });
  this.onShow = methods.onShow || ((elem) => {
    $(elem).removeClass('hide');
  });
  this.onHide = methods.onHide || ((elem) => {
    $(elem).addClass('hide');
  })

  this.applyFilters(filters);
}

TagService.prototype = {
  constructor: TagService,
  appendTag: function (group, obj, properties) {
    var disp = String(obj.display || obj.value);
    var $tag = $('<li><p>' + disp + '</p></li>');
    $tag.data('filter_data', obj.value);
    
    var $btn = $('<span class="close_btn">&times;</span>');
    $btn.appendTo($tag);

    if (properties.prefix) {
      $('<i style="margin-right: 5px; line-height: 20px; letter-spacing: 1px; font-size: 12px;">' + properties.prefix + '</i>').prependTo($tag);
    }
    if (properties.textColor) {
      $tag.css('color', properties.textColor);
    }
    if (properties.tagColor) {
      $tag.css('background-color', properties.tagColor);
    }

    var removeCallback = this.onRemove;
    $btn.on('click', function () {
      removeCallback(this, group, obj);
      $tag.remove();
    });
    $tag.appendTo($(this.element));
  },
  applyFilters: function (filters) {
    this.clearFilters();

    this.active = typeof filters === 'undefined' ? {} : filters;

    var applied = 0;
    $.each(this.active, (k, v) => {
      var properties = this.groups[k];
      if (typeof properties !== 'undefined') {
        if (Array.isArray(v)) {
          for (var i = 0; i < v.length; i++) {
            var val = String(v[i].display || v[i].value);
            if (typeof val !== 'undefined' && typeof val !== null && val.length > 0) {
              applied++;
              this.appendTag(k, v[i], properties);
            }
          }
        } else {
          var val = String(v.display || v.value);
          if (typeof val !== 'undefined' && typeof val !== null && val.length > 0) {
            applied++;
            this.appendTag(k, v, properties);
          }
        }
      }
    });

    if (applied > 0) {
      this.onShow(this.element);
    }
  },
  clearFilters: function () {
    this.active = [];
    $(this.element).empty();
    this.onHide(this.element);
  }
};

$.fn.filterTags = function (groups, methods, filters) {
  var service = new TagService(this, groups, methods, filters);
  $(this).data('TagService', service);
  return this;
}