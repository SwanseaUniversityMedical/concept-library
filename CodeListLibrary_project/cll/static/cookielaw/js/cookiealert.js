(function () {
    "use strict";

    var cookieAlert = document.querySelector(".cookiealert");
    var acceptCookies = document.querySelector(".acceptcookies");
    var rejectCookies = document.querySelector(".rejectcookies");
    var settingsCookie = document.querySelector(".preferencecookies");


    if (!cookieAlert) {
        return;
    }

    cookieAlert.offsetHeight; // Force browser to trigger reflow (https://stackoverflow.com/a/39451131)

    // Show the alert if we cant find the "acceptCookies" cookie
    if (!getCookie("acceptCookies")) {
        cookieAlert.classList.add("show");
    }

    if (getCookie("rejectCookies")) {
        cookieAlert.classList.remove("show");
    }

    if (getCookie("cookieSettings")) {
        cookieAlert.classList.remove("show");

    }


    function getCookie(cname) {
        var name = cname + "=";
        var decodedCookie = decodeURIComponent(document.cookie);
        var ca = decodedCookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) === ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }


    function setCookie(cname, cvalue, exdays) {
        var d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    }


    // When clicking on the agree button, create a 1 year
    // cookie to remember user's choice and close the banner
    acceptCookies.addEventListener("click", function () {
        setCookie("acceptCookies", true, 365);
        cookieAlert.classList.remove("show");
        // document.getElementById("accept_button").value=1;


        // dispatch the accept event
        window.dispatchEvent(new Event("cookieAlertAccept"))

    });


    rejectCookies.addEventListener("click", function () {
        cookieAlert.classList.remove("show");
        //document.getElementById("reject_button").value=1;
        setCookie("rejectCookies", false, 365);
        window.dispatchEvent(new Event("rejectCookiesAlert"))

    });

    settingsCookie.addEventListener("click", function () {
        cookieAlert.classList.remove("show");

         window.dispatchEvent(new Event("preferencecookiesAlert"))
    });


    // var ele = document.getElementById('link_privacy')
    //ele.addEventListener('click',function(){
    //   setCookie("acceptCookies", true, 365);
    // cookieAlert.classList.remove("show");

    // dispatch the accept event
    //window.dispatchEvent(new Event("cookieAlertAccept"))
    // });


})();

