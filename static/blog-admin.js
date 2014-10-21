/*
    JS that only runs within the blog admin interface
    depends on blog.js being included first
*/

gaeblog.buildDeleteForm = function(form, question) {
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
gaeblog.handleAdvancedLink = function(e) {
    var advanced_form = document.getElementById("advanced-section");
    gaeblog.toggle(advanced_form);
    gaeblog.stopEvent(e);
    return false;
};

gaeblog.advanced_link = document.getElementById("advanced-link");
if (gaeblog.advanced_link) {
    gaeblog.advanced_link.addEventListener("click", gaeblog.handleAdvancedLink, false);
}

/* view post page */
gaeblog.author_info = document.getElementById("comment-author-info");
gaeblog.author_radio = document.getElementById("author-choice-author");
if (gaeblog.author_radio) {
    gaeblog.author_radio.addEventListener("click", function(e) {
        gaeblog.author_info.style.display = "none";
        return false;
    }, false);
}

gaeblog.custom_radio = document.getElementById("author-choice-custom");
if (gaeblog.custom_radio) {
    gaeblog.custom_radio.addEventListener("click", function(e) {
        gaeblog.author_info.style.display = "block";
        return false;
    }, false);
}

gaeblog.trackback = document.getElementById("trackback");
if (gaeblog.trackback) {
    gaeblog.trackback_blog_name = document.getElementById("trackback-blog-name");
    gaeblog.pingback = document.getElementById("pingback");
    gaeblog.webmention = document.getElementById("webmention");

    gaeblog.trackback.addEventListener("click", function(e) {
        gaeblog.toggle(gaeblog.trackback_blog_name);
        if (gaeblog.trackback.checked) {
            gaeblog.pingback.checked = false;
            gaeblog.webmention.checked = false;
        }
    }, false);
    
    gaeblog.pingback.addEventListener("click", function(e) {
        if (gaeblog.pingback.checked) {
            gaeblog.trackback.checked = false;
            gaeblog.trackback_blog_name.style.display = "none";
            gaeblog.webmention.checked = false;
        }
    }, false);

    gaeblog.webmention.addEventListener("click", function(e) {
        if (gaeblog.webmention.checked) {
            gaeblog.trackback.checked = false;
            gaeblog.trackback_blog_name.style.display = "none";
            gaeblog.pingback.checked = false;
        }
    }, false);
}

/* images page */
gaeblog.forms = document.getElementsByTagName("form");
for (var i=0; i < gaeblog.forms.length; i++) {
    if (gaeblog.forms[i].className === "delete-form") {
        gaeblog.buildDeleteForm(gaeblog.forms[i], "Are you sure you want to permanently delete this image?\n\nAny references to it will be broken.");
    }
}

/* image page */
gaeblog.image_upload_form = document.getElementById("image-upload-form");
if (gaeblog.image_upload_form) {
    gaeblog.image_upload_form.addEventListener("submit", function(e) {
        if (gaeblog.image_upload_form.action.indexOf(gaeblog.BLOG_URL + '/admin/image') !== -1) {
            var url = gaeblog.BLOG_URL + '/admin/image?json=1';
            var submitImage = function(response) {
                gaeblog.image_upload_form.action = response.url;
                gaeblog.image_upload_form.submit();
            };
            gaeblog.getRequest(url, submitImage);
            gaeblog.stopEvent(e);
            return false;
        }
    }, false);
}

/* edit post page */
gaeblog.delete_form = document.getElementById("delete-form");
if (gaeblog.delete_form) {
    gaeblog.buildDeleteForm(gaeblog.delete_form, "Are you sure you want to permanently delete this post and all its comments?\n\nAny links to it will be broken.");
}

// don't display the preview button if the post is published
gaeblog.published_box = document.getElementById("published-box");
if (gaeblog.published_box) {
    gaeblog.published_box.addEventListener("click", function(e) {
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
    gaeblog.editorInit = function() {
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
            src.value = this.src.replace("=s100", "=s" + gaeblog.BLOG_IMAGE_PREVIEW_SIZE.toString());
            return false;
        };

        // clicking on pagination fires an ajax request to re-populate images
        var imagePage = function(e) {
            var hash = this.href.split("#")[1];
            var page = parseInt(hash.split("-")[1], 10);
            getImages(page);

            gaeblog.stopEvent(e);
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
                var url = gaeblog.BLOG_URL + '/admin/images?json=1&page=' + page.toString();
                var loadImages = function(response) {
                    last_page = response.last_page;
                    blog_images.push(response.images);
                    populateImages(response.page);
                };
                gaeblog.getRequest(url, loadImages);
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
            var editor = new nicEditor({iconsPath: gaeblog.BLOG_ICON_URL, fullPanel: true}).panelInstance('post-body');
        });
    };
    gaeblog.editorInit();
}
