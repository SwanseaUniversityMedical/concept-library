$.fn.pushToastNotification = function (notif) {
  var $this = $(this);
  var notifications = $this.data('ToastData') || $this.data('ToastData', []);

  notif = typeof notif === 'object' ? notif : { };
  var style = notif.style || 'error',
      desc = notif.desc || 'An error has occurred. Please try again.';
  
  for (var i = 0; i < notifications.length; i++) {
    var $notifcation = $(notifications[i]);
    $notifcation.css('bottom', ((i + 1) * 90 - (i * 30)).toString() + 'px');
  }

  var uuid = generateUUID();
  var $toast = $('<div class="filter_toast push" type=' + style + ' style="bottom: 30px" name=' + uuid + '><span id="icon"></span><div id="desc">' + desc + '</div></div>');
  $this.append($toast);
  notifications.push($toast[0]);

  setTimeout(function () {
    notifications = notifications.filter((item) => {
      return $(item).attr('name') !== uuid;
    });

    for (var i = 0; i < notifications.length; i++) {
      var $notifcation = $(notifications[i]);
      $notifcation.css('bottom', ((i + 1) * 30 + (i * 30)).toString() + 'px');
    }

    $toast.remove();
  }, 6400);
  
  return this;
}