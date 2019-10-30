var crtModelName = undefined;

var nodesMoving = {}; //here we store information from the tree plugin about the move, we grab in in the dnd_stop event and execute the move
var nodesMovingFromUpdate = false;



function populate_settings() {
    // Try to retrieve the current setting from the local storage
    let data = localStorage.getItem("21dataSettings");

    if (data != undefined) {
        try {
            // Try to deserialize the settings into an object
            let crtSettings = JSON.parse(data);

            // Set the appropriate parameters based on the configuration
            $('#themeSelect').val(crtSettings.theme);
        }
        catch {

        }
    }
}



function drop_nodes(nodeIds,path)
{
    let query={"nodes":nodeIds,"path":path};
    http_post("/dropnodes",JSON.stringify(query),null,null);
}


function populate_ui()
{
    var divs = $("div[id^='ui-layout']"); // all divs starting with "ui-layout"

    //for (var div of divs)
    //for (var index in divs)
    //for(const [index, div] of divs.entries())
    for (var index = 0; index < divs.length; index++)
    {

        var div = divs[index];
        let divTag = $("#"+div.id)
        var path = JSON.parse(divTag.attr('uiinfo'))['path'];
        var isLast = (index == (divs.length-1));

        http_post("_getlayout",JSON.stringify({"layoutNode":path}),div.id, isLast,function(isLast,status,data,params)   {
            var id = params;
            if (status==200)
            {
                $('#'+id).html(data);
            }
            else
            {
                if (id.includes("workbench"))
                {
                    console.log("get layout failed, we take a tree as default fallback")
                    $('#'+id).html('<div id="ui-tree-'+id+'">(loading of '+id+' failed, we provide the tree to fix things:)</div');
                }
            }
            //the trees
            var treeDivs =  $("#"+id+" div[id^='ui-tree']");
            for (var treeDiv of treeDivs)
            {
                var settings={};//check if there are local settings in the ui
                try
                {
                    settings = JSON.parse($("#"+treeDiv.id).attr('uiinfo'))['settings'];
                }
                catch{}
                var tree = new TreeCard(treeDiv.id,settings);
            }

            // the widgets
            var widgetDivs =  $("#"+id+" div[id^='ui-component']");
            for (var widgetDiv of widgetDivs)
            {
                var widgetAvatar = JSON.parse(widgetDiv.attributes.uiinfo.value).droppath;

                console.log("need a context menu for ",widgetDiv.id, "=> ", widgetAvatar);
                hook_context_menu(widgetDiv.id,widgetAvatar);
            }

            //if (isLast) populate_ui_complete();

        });
    }



}

function populate_file_list() {
    // Delete all files from the list
    $(".filenameRow").remove();

    // Get the list of files
    let data = http_get('/_upload');
    let files = []

    try {
        files = JSON.parse(data);
    }
    catch(err) {
        return;
    }

    for (let f of files) {
        $(`<div class="row filenameRow"><div class="col">` + f.name + `</div></div>`).insertBefore('#fileuploadRow');
    }
}

function initialize_upload() {
    // Get the files
    populate_file_list();

    // Initialize the file upload
    $('#fileupload').fileupload({
        dataType: 'text',
        add: function (e, data) {
            $('#fileuploadCol').append(`<button id="uploadButton" class="btn btn-primary" style="display: none">Upload</button>`);
            $('#uploadButton').click(function() {
                data.submit();
                $('#uploadStatusRow').fadeIn();
                $('#uploadStatusProgress').text("Progress: 0%");
            });
            $('#uploadButton').fadeIn();
        },
        done: function (e, data) {
            populate_file_list();

            console.log("successfully uploaded.");

            $('#uploadStatusProgress').text("Successfully uploaded!");
        },
        fail: function(e, data) {
            populate_file_list();

            console.log('failed uploading.');

            $('#uploadStatusProgress').text("Failed uploading!");
        },
        always: function(e, data) {
            $('#uploadButton').fadeOut(() => {
                $('#uploadButton').remove();
            });

            window.setTimeout(() => {
                $('#uploadStatusRow').fadeOut();
            }, 3000);
        },

        progressall: function (e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);

            $('#uploadStatusProgress').text("Progress: " + progress + " %");
        }
    });
}

function on_first_load () {


	//register menue calls#
    //$('.selectpicker').selectpicker();

    //populate_model_card_header();

	//tree_initialize();

    populate_settings();

    $('#applySettings').click(() => {
        let theme = $('#themeSelect').val();

        // Store all the settings into the local storage
        localStorage.setItem("21dataSettings", JSON.stringify({
            "theme": theme
        }));

        // Store the theme settings also separately, this shall be read at the beginning to set the proper theme.
        localStorage.setItem("21datalabTheme", theme);

        // Finally reload the page, which will trigger the theme change
        location.reload();
    });

    populate_ui();


    //myTree.tree_initialize();

    // This callback function is called when a node is dragged around, and moving
    $(document).on('dnd_move.vakata', function (e, data) {
        var t = $(data.event.target);
        let moveAllowed = false

        // First check if the node is moved inside the tree or outside
        if (!t.closest('.jstree').length) {
            // Node is moved outside the tree

            let nodes = data.data.nodes;
            // Some additional logic may be added here to determine whether the node can be moved or not,
            // some node types might support movig, drag and dropping, while others not

            // Check if the node is moved inside an item which supports dropping of nodes
            if (t.closest('.dropnodes').length) {
                // Node is moved over an allowed element which supports dropping of nodes
                moveAllowed = true;
            }
            else {
                moveAllowed = false;
            }
        }
        else {
            // Node is moved inside the tree, this shall be handled in the check_callback function of the tree,
            // because it provides more information about the drag and drop action
            moveAllowed = true;
        }

        if (moveAllowed) {
            // move allowed, remove the error icon and add the ok icon
            data.helper.find('.jstree-icon').removeClass('jstree-er').addClass('jstree-ok');
        }
        else {
            // move not allowed, remove the ok icon and add the error icon
            data.helper.find('.jstree-icon').removeClass('jstree-ok').addClass('jstree-er');
        }
    })

    $(document).on('dnd_start.vakata', function (e, data) {
        console.log("dnd_start.vakata");
        nodesMoving = {"vakata":"started"};
    });

    $(document).on('dnd_stop.vakata', function (e, data) {
        var t = $(data.event.target);
        nodesMoving.vakata = "stopped";
        // First check if the node is dropped inside the tree or outside
        if (!t.closest('.jstree').length) {
            // Node is moved outside the tree

            // Some additional logic may be added here to determine whether the node can be moved or not,
            // some node types might support movig, drag and dropping, while others not
            if (t.closest('.dropnodes').length) {
                // Node is dropped on an allowed element which supports dropping of nodes

                let div = t.closest('.dropnodes')[0];
                let droppath = JSON.parse($("#"+div.id).attr('uiinfo'))['droppath'];
                console.log("drop nodes outside of the tree, model path:"+droppath);
                //alert("add nodes "+String(nodes) + "to target"+String(info.path));
                drop_nodes(data.data.nodes,droppath);
            }
        }
        else
        {
            console.log("dnd_stop.vakata, moving in the tree");

            /* Node is dropped inside the tree, we handle this here as
                - inside the tree, the move is already node
                - here, we can bulk-do the action
                - here, we can do it completely over the backend
                */

            if (!("newParent" in nodesMoving))
            {
                console.log("we cant move without a parent");
                return false;
            }

            if (nodesMoving.newParent.startsWith('j'))
            {
                console.log("we can't move onto referencee");
                return false;
            }

            var nodesToMove = [];

            for (let nodeId of data.data.nodes)
            {

                if (nodeId.startsWith('j'))
                {
                    //if node to be moved or the target is a referencee node, we can't
                    console.log("can't move referencees, we skip this",nodeId);
                }
                else
                {
                    nodesToMove.push(nodeId);
                }
            }
            var query={"nodes":nodesToMove,"parent":nodesMoving.newParent};
            http_post("/move",JSON.stringify(query),null,null);//,tree_update);
        }
    });

    initialize_upload();

    // right mouse click
    /*
	document.querySelector('#ui-layout-workbench').addEventListener('contextmenu', function(e) {
		showContextMenu();
	    e.preventDefault();
	});
	*/



} //on_first_load;

function showContextMenu (){
    console.log("here context menu");
}


/*
function populate_ui_complete(){

    console.log("populate_ui_complete, this should be called only once at the very end!");
    var elem = $('#ui-component-workbench');
	elem.on('contextmenu', function(e) {

	    
        e.preventDefault();
        //var menu = prepare_context_menu(e);
        console.log("context");
        show_context_menu(e);
        //superCm.createMenu(menu, e);
        //return false;
    });
}
*/

function hook_context_menu(divId,modelPath)
{
     console.log("hook_context_menu()",divId," ",modelPath);
     var elem = $("#"+divId);
     elem.on('contextmenu', function(e) {
        e.preventDefault();
        console.log("context");
        show_context_menu(e,modelPath);
     });
}

function show_context_menu(e,modelPath)
{
   console.log("show_context_menu() ",modelPath);
    //get the current state from the backend
   http_post("_getbranchpretty",modelPath, e,null, function(obj,status,data,params)
        {
            if (status==200)
            {

                console.log("in show_context_menu(), back from http");

                var menu = prepare_context_menu(data,modelPath);
                superCm.createMenu(menu,params);
            }
        }
   );

}

function context_menu_click_show(option)
{
    let element = option.element;
    console.log(element, option.data[element]);
    if (option.data[element] == true)
    {
        //console.log("hide annotation and switch @",option.path);
        var data = option.data;
        data[element]=false;
        context_menu_set_visible_elements(option.path,data);
        superCm.destroyMenu();
    }
    else if (option.data[element] == false)
    {
        //console.log("show annotation and switch");

        var data = option.data;
        data[element]=true;
        context_menu_set_visible_elements(option.path,data);
        superCm.destroyMenu();
    }
    /*
    console.log("context_menu_click_show "+option.label);
    if (option.data.annotations == true)
    {
        console.log("hide annotation and switch @",option.path);
        var data = option.data;
        data.annotations=false;
        context_menu_set_visible_elements(option.path,data);
        superCm.destroyMenu();
    }
    else if (option.data.annotations == false)
    {
        console.log("show annotation and switch");

        var data = option.data;
        data.annotations=true;
        context_menu_set_visible_elements(option.path,data);
        superCm.destroyMenu();
    }
    */


}


function context_menu_set_visible_elements(modelPath,data)
{
        var query = [{browsePath:modelPath+".visibleElements",value:data}];

        http_post('/setProperties',JSON.stringify(query), null, this, (self,status,data,params) => {
            if (status>201)
            {
                //backend responded bad, we must set the frontend back

                console.log("context_menu_set_visible_elements",status);
            }
            else
            {
                console.log("context_menu_set_visible_elements ok");

            }
        });


}

function context_menu_click_delete(option)
{
    console.log("context_menu_click_delete "+option.label+" data" + option.data);

    http_post("/_delete",JSON.stringify(option.data),null,null,null);
    superCm.destroyMenu(); // hide it

}

function context_menu_click_test(option, contextMenuIndex, optionIndex)
{
    console.log("context_menu_click_test");
    var option = {

            icon: 'fas fa-cog',
            label : "settingsss",
            action: function(option, contextMenuIndex, optionIndex){ var opt = option; var idx = contextMenuIndex; var optIdx = optionIndex;
                context_menu_click_test(opt,idx,optIdx);
                }

    };

    superCm.setMenuOption(contextMenuIndex, optionIndex, option);
    superCm.updateMenu();

}

function context_menu_tag_select_click(option,contextMenuIndex, optionIndex)
{
    console.log("context_menu_tag_select_click",option);
    //make the true/false check box adjustment


    if (option.currentValue == true)
    {
        option.currentValue = false;
        option.icon = "far fa-square";
    }
    else
    {
        option.currentValue = true;
        option.icon = "far fa-check-square";
    }

    option.data[option.label]=option.currentValue;
    var query = [{browsePath:option.modelPath+".hasAnnotation.visibleTags",value:option.data}];
    http_post('/setProperties',JSON.stringify(query), null, this, null);
    superCm.setMenuOption(contextMenuIndex, optionIndex, option);
    superCm.updateMenu(allowHorzReposition = false, allowVertReposition = false);


}


function context_menu_click_function(option)
{
    console.log("context_menu_click_function, execute " + option.data);
    http_post("/_execute",JSON.stringify(option.data),null,null,null);
    superCm.destroyMenu(); // hide it
}

function prepare_context_menu(dataString,modelPath)
{
    //data is a string json containing the widget info
    var data = JSON.parse(dataString);
    var disableDirectModification = true;

    try
    {
        var targets = data.hasAnnotation.selectedAnnotations[".properties"].leaves;
        if (targets.length != 0)
        {
            console.log("have selected annotation");
            disableDirectModification = false;
        }
    }
    catch
    {
    }


    // let's create the context menue depending on the current status
    var menu= [

    // area direct modification, only if something is selected (annotation)
    {
        icon:"far fa-trash-alt",
        label:"delete",
        disabled : disableDirectModification,
        data: data.hasAnnotation.selectedAnnotations[".properties"].leaves,
        action : function(option, contextMenuIndex, optionIndex){context_menu_click_delete(option);}
    },
    {
        icon:"fas fa-external-link-alt",
        label:"show in model",
        disabled : disableDirectModification
    },
    {
        icon: 'fa fa-edit',   //Icon for the option
        label: 'modify',   //Label to be displayed for the option
        action: function(option, contextMenuIndex, optionIndex) {console.log("menu2");},   //The callback once clicked
        disabled: disableDirectModification
    },

    {
        separator : true
    }];


    //now comes the show/hide submenu
    let annotationsAction = "show";
    if (data.visibleElements[".properties"].value.annotations == true) annotationsAction = "hide";
    let backgroundAction = "show";
    if (data.visibleElements[".properties"].value.background == true) backgroundAction = "hide";
    let thresholdAction = "show";
    if (data.visibleElements[".properties"].value.thresholds == true) thresholdAction = "hide";
    let scoresAction = "show";
    if (data.visibleElements[".properties"].value.scores == true) scoresAction = "hide";

    let visibleTags = data.hasAnnotation.visibleTags[".properties"].value;

    // for switching on and off the annotation tags
    let annotationsSubmenu = [];
    for (tag in visibleTags)
    {
        let icon = "far fa-square";
        if (visibleTags[tag]== true) {icon = "far fa-check-square";}
        var entry = {
            icon:icon,
            label:tag,
            data:visibleTags,
            modelPath:modelPath,
            currentValue:visibleTags[tag],
            action: function(option, contextMenuIndex, optionIndex){
                    var opt = option;
                    var idx = contextMenuIndex; var
                    optIdx = optionIndex;
                    context_menu_tag_select_click(opt,idx,optIdx);
                }
        }

        annotationsSubmenu.push(entry);
    }





    let showSubmenu = [
        /*{
            disabled: false,
            icon: 'fas fa-columns',
            label: 'variables',
            submenu:[]
        },
        */
        {
            icon: 'far fa-dot-circle',
            label: scoresAction+' scores',
            element : "scores",
            data:data.visibleElements[".properties"].value,
            path:modelPath,
            action: function(option, contextMenuIndex, optionIndex){var opt = option; context_menu_click_show(opt);}
        },
        {
            icon: 'far fa-bookmark',
            label:annotationsAction+" annotations",
            element : "annotations",
            data:data.visibleElements[".properties"].value,
            path:modelPath,
            action: function(option, contextMenuIndex, optionIndex){var opt = option; context_menu_click_show(opt);},
            submenu : annotationsSubmenu
        },
        {
            icon: 'fas fa-layer-group',
            label:backgroundAction+" background",
            element:"background",
            data:data.visibleElements[".properties"].value,
            path:modelPath,
            action:function(option, contextMenuIndex, optionIndex){var opt = option; context_menu_click_show(opt);}
        },
        {
            icon: 'fas fa-arrows-alt-v',
            label: thresholdAction+' thresholds',
            element: "thresholds",
            data:data.visibleElements[".properties"].value,
            path:modelPath,
            action: function(option, contextMenuIndex, optionIndex){var opt = option; context_menu_click_show(opt);}

        }
    ];

    //add the show/hide to the menu
    menu.push({
        disabled: false,
        icon: 'fas fa-eye',
        label: 'show/hide',
        submenu: showSubmenu
        });

    //the "new area"
    var menuNew = [
        {separator :true},

        {
            icon: 'fa fa-plus',
            label: 'new',
            disabled: false,
            submenu: [
                {
                    icon: 'far fa-bookmark',
                    label:"annotation"
                },
                {
                    icon: 'fas fa-arrows-alt-v',
                    label: 'threshold'
                }
            ]
        }
    ]
    menu=menu.concat(menuNew);


    //user functions
    var menuUserFunctions =[{
            separator: true
        }];

    for (fkt of data.contextMenuFunctions[".properties"].leaves)
    {
        var entry={
            icon: 'fas fa-play-circle',
            label: '<font size="3" color="#d9b100">'+fkt+'</font>',
            data: fkt,
            action: function(option, contextMenuIndex, optionIndex){context_menu_click_function(option); }
        };
        menuUserFunctions.push(entry);
    }
    if (menuUserFunctions.length>1)
    {
        menu=menu.concat(menuUserFunctions);
    }


    var menuTail = [
        {
            separator: true
        },
        {
            icon: 'fas fa-cog',
            label : "settings",
            action: function(option, contextMenuIndex, optionIndex){ var opt = option; var idx = contextMenuIndex; var optIdx = optionIndex;
                context_menu_click_test(opt,idx,optIdx);
                }
        }
    ];

    menu = menu.concat(menuTail);
    return menu;
}


$( document ).ready(function() {
    console.log( "ready!" );
    on_first_load();
});



