/* JS that only runs within the blog admin interface */

var buildDeleteForm = function(form, question) {
    var handleDeleteForm = function(e) {
        var response = confirm(question);
        if (!response) {
            stopEvent(e);
            return false;
        }
    };
    form.addEventListener("submit", handleDeleteForm, false);
};

/* configuration page */
var handleAdvancedLink = function(e) {
    var advanced_form = document.getElementById("advanced-section");
    toggle(advanced_form);
    stopEvent(e);
    return false;
};

var advanced_link = document.getElementById("advanced-link");
if (advanced_link) {
    advanced_link.addEventListener("click", handleAdvancedLink, false);
}

/* view post page */
var author_info = document.getElementById("comment-author-info");
var author_radio = document.getElementById("author-choice-author");
if (author_radio) {
    author_radio.addEventListener("click", function(e) {
        author_info.style.display = "none";
        return false;
    }, false);
}

var custom_radio = document.getElementById("author-choice-custom");
if (custom_radio) {
    custom_radio.addEventListener("click", function(e) {
        author_info.style.display = "block";
        return false;
    }, false);
}

/* images page */
var forms = document.getElementsByTagName("form");
for (var i=0; i < forms.length; i++) {
    if (forms[i].className === "delete-form") {
        buildDeleteForm(forms[i], "Are you sure you want to permanently delete this image?\n\nAny references to it will be broken.");
    }
}

/* image page */
var image_upload_form = document.getElementById("image-upload-form");
if (image_upload_form) {
    image_upload_form.addEventListener("submit", function(e) {
        if (image_upload_form.action.indexOf(BLOG_URL + '/admin/image') !== -1) {
            var url = BLOG_URL + '/admin/image?json=1';
            var submitImage = function(response) {
                image_upload_form.action = response.url;
                image_upload_form.submit();
            };
            getRequest(url, submitImage);
            stopEvent(e);
            return false;
        }
    }, false);
}

/* edit post page */
var delete_form = document.getElementById("delete-form");
if (delete_form) {
    buildDeleteForm(delete_form, "Are you sure you want to permanently delete this post and all its comments?\n\nAny links to it will be broken.");
}

// don't display the preview button if the post is published
var published_box = document.getElementById("published-box");
if (published_box) {
    published_box.addEventListener("click", function(e) {
        var preview_button = document.getElementById("preview-button");
        if (this.checked) {
            preview_button.style.display = "none";
        }
        else {
            preview_button.style.display = "block";
        }
        return false;
    }, false);
}

// check to make sure this only runs if the editor code exists
if ("nicEditor" in window) {
    var div_id = "editor-images";
    var blog_images = [];
    var last_page = 0;

    // clicking images makes them auto-fill the src field
    var selectImage = function(e) {
        // remove an active class from the others and then add it to this image
        var div = document.getElementById(div_id);
        var others = div.getElementsByTagName('img');
        var active_class = "editor-image-selected";
        for (var i=0; i < others.length; i++) {
            var other = others[i];
            if (other.className.indexOf(active_class) !== -1) {
                other.className = other.className.replace(active_class, "").trim();
            }
        }
        this.className = (this.className + " " + active_class).trim();
        var src = document.getElementById("src");
        src.value = this.src.replace("=s100", "=s" + BLOG_IMAGE_PREVIEW_SIZE.toString());
        return false;
    };

    // clicking on pagination fires an ajax request to re-populate images
    var imagePage = function(e) {
        var hash = this.href.split("#")[1];
        var page = parseInt(hash.split("-")[1], 10);
        getImages(page);

        stopEvent(e);
        return false;
    };

    var populateImages = function(page) {
        var image_urls = blog_images[page];
        var div = document.getElementById(div_id);
        div.innerHTML = '';
        for (var i=0; i < image_urls.length; i++) {
            var image_url = image_urls[i];
            var img = new bkElement('img');
            img.setAttributes({src: image_url + "=s100", alt: "Image Preview"});
            img.addEvent("click", selectImage, false);
            img.appendTo(div);
        }
        if (last_page > 0) {
            var p = new bkElement('p');
            if (page > 0) {
                var a = new bkElement('a');
                a.setAttributes({href: '#page-' + (page - 1).toString()});
                a.innerHTML = '&lt; Newer Images';
                a.addEvent("click", imagePage, false);
                a.appendTo(p);
            }
            if (page < last_page) {
                var a = new bkElement('a');
                a.setAttributes({href: '#page-' + (page + 1).toString()});
                a.innerHTML = 'Older Images &gt;';
                a.addEvent("click", imagePage, false);
                a.appendTo(p);
            }
            p.appendTo(div);
        }
    };

    // function to get images one batch at a time via ajax
    var getImages = function(page) {
        if (blog_images.length > page) {
            populateImages(page);
        }
        else {
            var url = BLOG_URL + '/admin/images?json=1&page=' + page.toString();
            var loadImages = function(response) {
                last_page = response.last_page;
                blog_images.push(response.images);
                populateImages(response.page);
            };
            getRequest(url, loadImages);
        }
    };

    // save a copy of the original function
    var nicImageButtonOrig = nicImageButton;

    // monkey patch the image button in the editor to use our own images
    var blogImageButton = nicEditorAdvancedButton.extend({
        addPane: function() {
            var div = document.getElementById(div_id);
            if (!div) {
                // add images to a div that is attached to the pane
                div = new bkElement('div');
                div.id = div_id;
                this.pane.append(div);
                getImages(0);
            }

            // standard plugin code to add the form
            this.im = this.ne.selectedInstance.selElm().parentTag('IMG');
            this.addForm({
                '' : {type : 'title', txt : 'Add/Edit Image'},
                'src' : {type : 'text', txt : 'URL', 'value' : 'http://', style : {width: '150px'}},
                'alt' : {type : 'text', txt : 'Alt Text', style : {width: '100px'}},
                'align' : {type : 'select', txt : 'Align', options : {none : 'Default','left' : 'Left', 'right' : 'Right'}}
            },this.im);
        },

        // use the original submit function
        submit: nicImageButtonOrig.prototype.submit
    });

    // replace the original plugin with this one
    nicImageButton = blogImageButton;

    bkLib.onDomLoaded(function() {
        var editor = new nicEditor({iconsPath: BLOG_ICON_URL, fullPanel: true}).panelInstance('post-body');
    });
}
