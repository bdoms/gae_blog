/* JS for the blog to run on all pages */

var DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

var converted = [];
var convert_timestamp = function(el) {
    for (var i=0; i < converted.length; i++) {
        if (converted[i] == el) {
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
    if (hours == 0) {hours = 12;}

    var minutes = local.getMinutes().toString();
    if (minutes.length < 2) {minutes = "0" + minutes;}

    var time_string = hours.toString() + ":" + minutes + " " + ampm;

    el.innerHTML = date_string + " at " + time_string;
};


/* post page */
var paragraphs = document.getElementsByTagName("p");
for (var i=0; i < paragraphs.length; i++) {
    if (paragraphs[i].className == "post-timestamp" || paragraphs[i].className == "comment-timestamp") {
        convert_timestamp(paragraphs[i]);
    }
}

var comment_link = document.getElementById("comment-link");
if (comment_link) {
    comment_link.addEventListener("click", function(e) {
        var comment_form = document.getElementById("comment-form");
        if (comment_form.style.display == "none") {
            comment_form.style.display = "block";
        }
        else {
            comment_form.style.display = "none";
        }
        return false;
    }, false);
}
