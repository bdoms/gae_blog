/* JS for the blog to run on all pages */

var gaeblog = gaeblog || {};

gaeblog.DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
gaeblog.MONTHS = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

gaeblog.convert_timestamp = function(el) {
    var iso = el.getAttribute("datetime");
    var local = new Date(iso);
    var day_and_month = gaeblog.DAYS[local.getDay()] + ", " + gaeblog.MONTHS[local.getMonth()];
    var date_string = day_and_month + " " + local.getDate().toString() + ", " + local.getFullYear().toString();

    var hours = local.getHours();
    var ampm = "AM";
    if (hours > 11) {ampm = "PM";}
    if (hours > 12) {hours -= 12;}
    if (hours === 0) {hours = 12;}

    var minutes = local.getMinutes().toString();
    if (minutes.length < 2) {minutes = "0" + minutes;}

    var time_string = hours.toString() + ":" + minutes + " " + ampm;

    el.innerHTML = date_string + " at " + time_string;
};

gaeblog.stopEvent = function(e) {
    if (e.stopPropagation) {e.stopPropagation();}
    else {e.cancelBubble = true;}

    if (e.preventDefault) {e.preventDefault();}
    else {e.returnValue = false;}
};

gaeblog.toggle = function(el) {
    if (el.style.display === "none") {
        el.style.display = "block";
    }
    else {
        el.style.display = "none";
    }
};

gaeblog.getRequest = function(url, callback) {
    var req = new XMLHttpRequest;
    req.open("GET", url, true);
    req.onreadystatechange = function() {
        if (req.readyState === 4 && req.status === 200) {
            callback(JSON.parse(req.responseText));
        }
    };
    req.send(null);
    return req;
};

/* post page */
gaeblog.times = document.getElementsByTagName("time");
for (var i=0; i < gaeblog.times.length; i++) {
    gaeblog.convert_timestamp(gaeblog.times[i]);
}

gaeblog.handlePublicSubmit = function(e) {
    var form = this;
    var submit_token = document.getElementById("submit-token");
    if (submit_token) {
        return true;
    }
    else if (!form.getAttribute("data-locked")) {
        form.setAttribute("data-locked", true);
        var url = gaeblog.BLOG_URL + '/verify?url=' + form.action;
        var submitWithToken = function(response) {
            var input = document.createElement("input");
            input.name = "token";
            input.id = "submit-token";
            input.type = "hidden";
            input.value = response.token;
            form.appendChild(input);
            form.submit();
        };
        gaeblog.getRequest(url, submitWithToken);
    }
    gaeblog.stopEvent(e);
    return false;
};

gaeblog.comment_form = document.getElementById("comment-form");
if (gaeblog.comment_form) {
    gaeblog.comment_form.addEventListener("submit", gaeblog.handlePublicSubmit, false);
}

gaeblog.handleCommentLink = function(e) {
    gaeblog.toggle(gaeblog.comment_form);
    if (gaeblog.comment_form.style.display === "none") {
        gaeblog.stopEvent(e);
    }
};

gaeblog.comment_link = document.getElementById("comment-link");
if (gaeblog.comment_link) {
    gaeblog.comment_link.addEventListener("click", gaeblog.handleCommentLink, false);
}

/* contact page */
gaeblog.contact_form = document.getElementById("contact-form");
if (gaeblog.contact_form) {
    gaeblog.contact_form.addEventListener("submit", gaeblog.handlePublicSubmit, false);
}
