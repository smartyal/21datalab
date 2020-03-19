/*!
 * Super Context Menu
 * Created by EZ17-1, pwnedgod @ github
 */
'use strict';

window.superCm = function(msie) {

    var settings = {
        'minWidth': null,
        'maxHeight': null,
        'autoClose': false,
        'searchBar': false,
        'searchBarPlaceholder': 'Search...',
        'zIndex': 50
    };

    var cmTemplate = $('<div>').addClass('context-menu')
        .append(
            $('<div>').addClass('context-menu-options')
        );

    var cmOptTemplate = $('<div>');

    var cmSearchTemplate = $('<div>').addClass('context-menu-search')
        .append(
            $('<input>').prop({ 'type':'text', 'placeholder': settings.searchBarPlaceholder })
        );

    var optIconTemplate = $('<i>').addClass('option-icon');
    var optTextTemplate = $('<span>').addClass('option-text');
    var optSeparatorTemplate = $('<hr>').addClass('option-separator');

    var cms = [];

    var activeOpt = null;

    function getOpts(cmIndex, actualOpts)
    {
        var cm = cms[cmIndex];
        return cm.search.result && !actualOpts ? cm.search.result : cm.opts;
    }

    function getOptContainer(cmIndex)
    {
        return cms[cmIndex].element.find('.context-menu-options');
    }

    function getOptElements(cmIndex)
    {
        return getOptContainer(cmIndex).children();
    }

    function getOptElement(cmIndex, optIndex)
    {
        return getOptContainer(cmIndex).children().eq(optIndex);
    }

    function setCurrentActiveOver(cmIndex, optIndex)
    {
        if(activeOpt == null || activeOpt.cmIndex != cmIndex || activeOpt.optIndex != optIndex) {
            if(activeOpt != null) {
                let cmOptElement = getOptElement(activeOpt.cmIndex, activeOpt.optIndex);

                if(cmOptElement.hasClass('active')) {
                    cmOptElement.removeClass('active');
                }
            }

            if(cmIndex != -1 && optIndex != -1) {
                let cmOptElement = getOptElement(cmIndex, optIndex);

                if(!cmOptElement.hasClass('active')) {
                    cmOptElement.addClass('active');
                }

                activeOpt = {
                    'cmIndex': cmIndex,
                    'optIndex': optIndex
                };
            } else {
                activeOpt = null;
            }
        }
    }

    function setActiveOptSubmenu(cmIndex, optIndex)
    {
        var activeSubmenu = cms[cmIndex].activeSubmenu;
        if(activeSubmenu != optIndex) {
            if(activeSubmenu != -1) {
                let cmOptElement = getOptElement(cmIndex, activeSubmenu);

                if(cmOptElement.hasClass('active-submenu')) {
                    cmOptElement.removeClass('active-submenu');
                }
            }

            if(optIndex != -1) {
                let cmOptElement = getOptElement(cmIndex, optIndex);

                if(!cmOptElement.hasClass('active-submenu')) {
                    cmOptElement.addClass('active-submenu');
                }
            }

            cms[cmIndex].activeSubmenu = optIndex;
        }
    }

    function destroyCm(cmIndex)
    {
        if(cmIndex === undefined) {
            cmIndex = 0;
        }

        if(activeOpt != null && cmIndex <= activeOpt.cmIndex) {
            setCurrentActiveOver(-1, -1);
        }

        for(let i = cms.length - 1; i >= cmIndex; i--) {
            cms.pop().element.remove();
        }
    }

    function updateCm(cmIndex)
    {
        var cm = cms[cmIndex];

        var opts = getOpts(cmIndex, false);

        if(opts.length == 0) {
            opts = [
                {
                    'label': '&lt; Empty &gt;',
                    'disabled': true
                }
            ];
        }

        opts.forEach(function(opt, optIndex) {
            var cmOptElement = getOptElement(cmIndex, optIndex);

            var separator = opt.separator !== undefined;
            var icon = opt.icon !== undefined && opt.icon;
            var label = opt.label !== undefined && opt.label;
            var disabled = opt.disabled !== undefined && opt.disabled;
            var action = opt.action !== undefined && opt.action;
            var submenu = opt.submenu !== undefined && opt.submenu;

            if(cmOptElement.length) {
                cmOptElement.empty();
                cmOptElement.off();
                cmOptElement.removeClass();
            } else {
                cmOptElement = cmOptTemplate.clone();
                cmOptElement.appendTo(getOptContainer(cmIndex));
            }

            if(separator) {
                if(!cmOptElement.hasClass('context-menu-separator')) {
                    cmOptElement.addClass('context-menu-separator');
                }

                cmOptElement.append(
                    optSeparatorTemplate.clone()
                );

                return;
            }

            if(icon) {
                cmOptElement.append(
                    optIconTemplate.clone().addClass(opt.icon)
                );
            }

            if(label) {
                cmOptElement.append(
                    optTextTemplate.clone().html(opt.label)
                );
            }

            if(disabled) {
                if(!cmOptElement.hasClass('context-menu-disabled')) {
                    cmOptElement.addClass('context-menu-disabled');
                }
                return;
            }

            if(action) {
                cmOptElement.click(function() {
                    if(settings.autoClose) {
                        destroyCm();
                    } else {
                        destroyCm(cmIndex + 1);
                        setActiveOptSubmenu(cmIndex, -1);
                    }

                    opt.action(opt, cmIndex, optIndex);
                });
            }

            if(submenu) {
                cmOptElement.on('submenu', function() {
                    if(cm.activeSubmenu == optIndex) {
                        return;
                    }

                    var submenuIndex = cmIndex + 1;

                    setActiveOptSubmenu(cmIndex, optIndex);
                    destroyCm(submenuIndex);

                    showCm(opt.submenu, submenuIndex, {
                        x: cm.position.x + cm.element.outerWidth(),
                        y: cm.position.y + this.offsetTop - this.parentElement.scrollTop - parseInt(getOptContainer(cmIndex).css('padding-top'))
                    });
                });

                cmOptElement.mouseenter(function() {
                    setCurrentActiveOver(cmIndex, optIndex);
                    $(this).trigger('submenu');
                });

                if(!cmOptElement.hasClass('context-menu-submenu')) {
                    cmOptElement.addClass('context-menu-submenu');
                }
            } else {
                cmOptElement.mouseenter(function() {
                    setCurrentActiveOver(cmIndex, optIndex);
                    setActiveOptSubmenu(cmIndex, -1);
                    destroyCm(cmIndex + 1);
                });

                if(!cmOptElement.hasClass('context-menu-option')) {
                    cmOptElement.addClass('context-menu-option');
                }
            }

            cmOptElement.mouseleave(function() {
                if(activeOpt.cmIndex == cmIndex && activeOpt.optIndex == optIndex) {
                    setCurrentActiveOver(-1, -1);
                }
            });
        });

        var cmElementChildren = getOptElements(cmIndex);
        for(let i = cmElementChildren.length - 1; i >= opts.length; i--) {
            cmElementChildren.eq(i).remove();
        }
    }

    function updateCmPosition(cmIndex, repositionX, repositionY)
    {
        if(repositionX === undefined) {
            repositionX = true;
        }

        if(repositionY === undefined) {
            repositionY = true;
        }

        var cm = cms[cmIndex];

        if(cmIndex > 0) {
            var parentCmIndex = cmIndex - 1;
            var parentCm = cms[parentCmIndex];
            var activeSubmenu = getOptElement(parentCmIndex, parentCm.activeSubmenu);

            cm.position = {
                'x': parentCm.position.x + parentCm.element.outerWidth(),
                'y': parentCm.position.y + activeSubmenu[0].offsetTop - activeSubmenu[0].parentElement.scrollTop - parseInt(getOptContainer(cmIndex).css('padding-top'))
            };
        }

        if(repositionX) {
            var cmElementWidth = cm.element.outerWidth();
            if(cm.position.x - $(window).scrollLeft() + cmElementWidth >= $(window).innerWidth()) {
                cm.position.x -= cmElementWidth;

                if(cmIndex > 0) {
                    cm.position.x -= parentCm.element.outerWidth();
                }

                if(cm.position.x < $(window).scrollLeft()) {
                    cm.position.x = $(window).scrollLeft();
                }
            }

            cm.element.css('left', cm.position.x);
        }

        var cmElementHeight = cm.element.outerHeight();
        if(repositionY) {
            if(cm.position.y - $(window).scrollTop() + cmElementHeight >= $(window).innerHeight()) {
                cm.position.y -= cmElementHeight;

                if(cmIndex > 0) {
                    var paddingBottom = parseInt(getOptContainer(cmIndex).css('padding-bottom'));
                    var lastOpt = getOptElements(cmIndex).last();
                    var paddingTop = parseInt(getOptContainer(cmIndex).css('padding-top'));
                    cm.position.y += paddingBottom + paddingTop + lastOpt.outerHeight();
                }

                if(cm.position.y < $(window).scrollTop()) {
                    cm.position.y = $(window).scrollTop();
                }
            }

            cm.element.css('top', cm.position.y);
        }

        if(settings.maxHeight === null) {
            var leftoverHeight = cm.position.y - $(window).scrollTop();
            if(msie) {
                let leftoverWindowHeight = $(window).innerHeight() - leftoverHeight;
                if(cmElementHeight > leftoverWindowHeight) {
                    cm.element.css('height', leftoverWindowHeight);
                }
            } else {
                cm.element.css('max-height', 'calc(100vh - ' + leftoverHeight + 'px)');
            }
        } else {
            if(msie) {
                if(cmElementHeight > settings.maxHeight) {
                    cm.element.css('height', settings.maxHeight);
                }
            } else {
                cm.element.css('max-height', settings.maxHeight);
            }
        }

        if(settings.minWidth !== null) {
            cm.element.css('min-width', settings.minWidth);
        }

        cm.element.css('z-index', settings.zIndex + cmIndex);
    }

    function populateSearchResult(result, opts, keyword)
    {
        opts.forEach(function(opt) {
            var match = false;

            if(opt.label !== undefined && opt.label) {
                var label = opt.label.toLowerCase();

                if(label && label.indexOf(keyword) != -1) {
                    result.push(opt);
                    match = true;
                }
            }

            if(!match && opt.submenu !== undefined && opt.submenu.length) {
                populateSearchResult(result, opt.submenu, keyword);
            }
        });
    }

    function updateSearch(cmIndex)
    {
        var cm = cms[cmIndex];
        if(cm.search.input === null) {
            return;
        }

        var keyword = cm.search.input.val().trim();
        if(keyword == '') {
            cm.search.result = null;
            updateCm(cmIndex);
            return;
        }

        setCurrentActiveOver(-1, -1);

        var result = [];

        populateSearchResult(result, cm.opts, keyword.toLowerCase());
        cm.search.result = result;
    }

    function showCm(opts, cmIndex, position)
    {
        var cmElement = cmTemplate.clone();

        if(settings.searchBar && cmIndex == 0) {
            var cmSearch = cmSearchTemplate.clone();
            cmSearch.prependTo(cmElement);
        }

        var cm = {
            'element': cmElement,
            'position': position,
            'opts': opts,
            'activeSubmenu': -1,
            'search': {
                'input': cmSearch ? cmSearch.find('input') : null,
                'result': null
            }
        };
        cms.push(cm);

        getOptContainer(cmIndex).scroll(function() {
            setActiveOptSubmenu(cmIndex, -1);
            destroyCm(cmIndex + 1);
        });

        setCurrentActiveOver(-1, -1);
        activeOpt = {
            'cmIndex': cmIndex,
            'optIndex': -1
        };

        cmElement.appendTo(document.body);
        updateCm(cmIndex);
        updateCmPosition(cmIndex);

        if(cmSearch) {
            cm.search.input
                .on('input', function() {
                    destroyCm(cmIndex + 1);
                    updateSearch(cmIndex);
                    updateCm(cmIndex);
                    updateCmPosition(cmIndex, true, false);
                })
                .focus();
        }
    }

    function isSelectable(cmIndex, optIndex)
    {
        var opt = getOpts(cmIndex, false)[optIndex];
        return opt.separator === undefined && (opt.disabled === undefined || !opt.disabled);
    }

    function findSuitableSelectable(cmIndex, optIndex, reverse)
    {
        var optElements = getOptElements(cmIndex);

        if(optIndex >= optElements.length) {
            optIndex = 0;
        } else if(optIndex < 0) {
            optIndex = optElements.length - 1;
        }

        var currentOptIndex = optIndex;
        while(!isSelectable(cmIndex, currentOptIndex)) {
            currentOptIndex += reverse ? -1 : 1;

            if(currentOptIndex == optIndex) {
                return -1;
            }

            if(currentOptIndex >= optElements.length) {
                currentOptIndex = 0;
            } else if(currentOptIndex < 0) {
                currentOptIndex = optElements.length - 1;
            }
        }

        return currentOptIndex;
    }

    function activeUp()
    {
        if(activeOpt == null || activeOpt.optIndex == -1) {
            var cmIndex = cms.length - 1;
            var cmOpts = getOpts(cmIndex);

            if(cmOpts.length <= 0) {
                return;
            }

            setCurrentActiveOver(cmIndex, cmOpts.length - 1);
            return;
        }

        var previousOptIndex = findSuitableSelectable(activeOpt.cmIndex, activeOpt.optIndex - 1, true);

        if(previousOptIndex != -1) {
            setCurrentActiveOver(activeOpt.cmIndex, previousOptIndex);
        }
    }

    function activeDown()
    {
        if(activeOpt == null || activeOpt.optIndex == -1) {
            var cmIndex = cms.length - 1;
            var cmOpts = getOpts(cmIndex);

            if(cmOpts.length <= 0) {
                return;
            }

            setCurrentActiveOver(cmIndex, 0);
            return;
        }

        var nextOptIndex = findSuitableSelectable(activeOpt.cmIndex, activeOpt.optIndex + 1, false);

        if(nextOptIndex != -1) {
            setCurrentActiveOver(activeOpt.cmIndex, nextOptIndex);
        }
    }

    $(document).on('mousedown.scm contextmenu.scm', '.context-menu, .opt-text, .opt-icon, .opt-separator', function(e) {
        e.stopPropagation();
    });

    $(document).on('keydown.scm', function(e) {
        if(e.key == 'Escape' || e.which == 27) {
            destroyCm();
        }

        if(cms.length > 0) {
            if(e.key == 'ArrowUp' || e.which == 38) {
                e.preventDefault();
                activeUp();
            } else if(e.key == 'ArrowDown' || e.which == 40) {
                e.preventDefault();
                activeDown();
            } else if(e.key == 'Enter' || e.which == 13) {
                e.preventDefault();
                getOptElement(activeOpt.cmIndex, activeOpt.optIndex)
                    .click();
            } else if(e.key == 'ArrowLeft' || e.which == 37) {
                if(activeOpt != null && activeOpt.cmIndex > 0) {
                    e.preventDefault();
                    var parentCmIndex = activeOpt.cmIndex - 1;
                    var parentCm = cms[parentCmIndex];

                    var parentContextActiveSubmenu = parentCm.activeSubmenu;
                    destroyCm(activeOpt.cmIndex);
                    setActiveOptSubmenu(parentCmIndex, -1);

                    setCurrentActiveOver(parentCmIndex, parentContextActiveSubmenu);
                }
            } else if(e.key == 'ArrowRight' || e.which == 39) {
                if(activeOpt != null && activeOpt.optIndex != -1) {
                    var optElement = getOptElement(activeOpt.cmIndex, activeOpt.optIndex);

                    if(optElement.hasClass('context-menu-submenu')) {
                        e.preventDefault();
                        optElement.trigger('submenu');
                    }
                }
            }
        }
    });

    $(document).on('mousedown.scm', function() {
        destroyCm();
    });

    $(window).on('scroll.scm resize.scm', function() {
        destroyCm();
    });

    return {
        settings: settings,
        createMenu: function(opts, event) {
            destroyCm();
            showCm(opts, 0, { x: event.pageX, y: event.pageY });
        },
        destroyMenu: function() {
            destroyCm();
        },
        updateMenu: function(repositionX, repositionY) {
            cms.forEach(function(cm, cmIndex) {
                updateSearch(cmIndex);
                updateCm(cmIndex);
                updateCmPosition(cmIndex, repositionX, repositionY);
            });
        },
        getMenuOptions: function(cmIndex) {
            return cms[cmIndex].opts;
        },
        addMenuOption: function(cmIndex, opt, optIndex) {
            if(optIndex !== undefined) {
                cms[cmIndex].opts.splice(optIndex, 0, opt);
            } else {
                cms[cmIndex].opts.push(opt);
            }
        },
        addMenuOptions: function(cmIndex, opts, optIndex) {
            if(optIndex !== undefined) {
                Array.prototype.splice.apply(cms[cmIndex].opts, [optIndex, 0].concat(opts));
            } else {
                cms[cmIndex].opts = cms[cmIndex].opts.concat(opts);
            }
        },
        deleteMenuOption: function(cmIndex, optIndex) {
            cms[cmIndex].opts.splice(optIndex, 1);
        },
        setMenuOption: function(cmIndex, optIndex, opt) {
            cms[cmIndex].opts[optIndex] = opt;
        },
        setMenuOptions: function(cmIndex, opts) {
            cms[cmIndex].opts = opts;
        },
		isOpen: function() {
			return $(".context-menu").length !== 0;
		},
    };

}(navigator.appName == 'Microsoft Internet Explorer' || /Trident/.test(navigator.userAgent) || /rv:11/.test(navigator.userAgent));
