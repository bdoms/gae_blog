/* JS for the blog to run on all pages */

var DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

var converted = [];
var convert_timestamp = function(el) {
    for (var i=0; i < converted.length; i++) {
        if (converted[i] === el) {
            return;
        }
    }
    converted.push(el);

    var seconds = el.getElementsByTagName("input")[0].value;
    // convert from seconds to ms
    var utc_ms = parseInt(seconds) * 1000;
    var local = new Date(utc_ms);
    var day_and_month = DAYS[local.getDay()] + ", " + MONTHS[local.getMonth()];
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

var stopEvent = function(e) {
    if (e.stopPropagation) {e.stopPropagation();}
    else {e.cancelBubble = true;}

    if (e.preventDefault) {e.preventDefault();}
    else {e.returnValue = false;}
};

var toggle = function(el) {
    if (el.style.display === "none") {
        el.style.display = "block";
    }
    else {
        el.style.display = "none";
    }
};

var getRequest = function(url, callback) {
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
var paragraphs = document.getElementsByTagName("p");
for (var i=0; i < paragraphs.length; i++) {
    var p = paragraphs[i];
    if (p.className === "post-timestamp" || p.className === "comment-timestamp") {
        convert_timestamp(p);
    }
}

var handlePublicSubmit = function(e) {
    var form = this;
    var submit_token = document.getElementById("submit-token");
    if (submit_token) {
        return true;
    }
    else if (!form.getAttribute("data-locked")) {
        form.setAttribute("data-locked", true);
        var url = BLOG_URL + '/verify?url=' + form.action;
        var submitWithToken = function(response) {
            var input = document.createElement("input");
            input.name = "token";
            input.id = "submit-token";
            input.type = "hidden";
            input.value = response.token;
            form.appendChild(input);
            form.submit();
        };
        getRequest(url, submitWithToken);
    }
    stopEvent(e);
    return false;
};

var comment_form = document.getElementById("comment-form");
if (comment_form) {
    comment_form.addEventListener("submit", handlePublicSubmit, false);
}

var handleCommentLink = function(e) {
    toggle(comment_form);
    stopEvent(e);
    return false;
};

var comment_link = document.getElementById("comment-link");
if (comment_link) {
    comment_link.addEventListener("click", handleCommentLink, false);
}

/* contact page */
var contact_form = document.getElementById("contact-form");
if (contact_form) {
    contact_form.addEventListener("submit", handlePublicSubmit, false);
}
