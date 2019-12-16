var crtModelName = undefined;

var nodesMoving = {}; //here we store information from the tree plugin about the move, we grab in in the dnd_stop event and execute the move
var nodesMovingFromUpdate = false;

var eventSource = 0;


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

function initialize_progress_bar()
{
    eventSource = new EventSource('/event/stream');

    // This callback handles messages that have no event field set, should not be used in our case
    eventSource.onmessage = (e) => {
        // Do something - event data etc will be in e.data
        console.log("event",e,e.data);
    };

    // Handler for events of type 'system.progress' only
    eventSource.addEventListener('system.progress', (e) => {
        // Do something - event data will be in e.data,
        // message will be of type 'eventType'

        let data = e.data;
        //replace potential single quotes
        data = data.replace(/\'/g, "\"");
        var valeur=JSON.parse(data).value;
        valeur = valeur*100;
        console.log("EVENT system.progress" + valeur );
        $('.progress-bar').css('width', valeur+'%').attr('aria-valuenow', valeur);
        if (valeur != 100)
        {
            $('.progress-bar').text(JSON.parse(data).function);
        }
        else
        {
            $('.progress-bar').text("");
        }
    });

     eventSource.addEventListener('system.status', (e) => {
        // Do something - event data will be in e.data,
        // message will be of type 'eventType'

        let data = e.data;
        //replace potential single quotes
        data = data.replace(/\'/g, "\"");
        var parsed = JSON.parse(data);
        console.log("EVENT system-status" + parsed.text );
        $('#system-status').text(parsed.text);
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

    initialize_progress_bar();
    initialize_context_menu();

} //on_first_load;


function initialize_context_menu()
{
    // make the modals needed
    var modal = document.createElement('div');
    modal.id = "annotationedit";
    modal.className = "modal fade";
    modal.setAttribute("tabindex","-1");
    modal.setAttribute("role","dialog");
    modal.setAttribute("aria-labelledby","myModalLabel");

    var modalCode = `
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h4 class="modal-title" id="annotationedittitle">Edit Selection</h4>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    </div>

                    <div class="modal-body" id ="annotationeditbody">
                        <div class="form-group row">
                            <div class="col-10" id="annotationeditnodepath">browsepath</div>
                        </div>

                        <div class="form-group row" id="annotationeditmin">
                            <label class="col-3">min</label>
                            <div class="col-9">
                                <input type="text" id="annotationeditminval" class="form-control edit-modal-input" value="val">
                            </div>
                        </div>
                        <div class="form-group row" id="annotationeditmax">
                            <label class="col-3">max</label>
                            <div class="col-9">
                                <input type="text" id="annotationeditmaxval" class="form-control edit-modal-input" value="val">
                            </div>
                        </div>
                        <div class="form-group row" id="annotationeditstart" hidden>
                            <label class="col-3">start</label>
                            <div class="col-9">
                                <input type="text" id="annotationeditstartval" class="form-control edit-modal-input" value="start">
                            </div>
                        </div>
                        <div class="form-group row" id="annotationeditend" hidden>
                            <label class="col-3">end</label>
                            <div class="col-9">
                                <input type="text" id="annotationeditendval" class="form-control edit-modal-input" value="start">
                            </div>
                        </div>
                       <div class="form-group row" id="annotationedittags" hidden>
                            <label class="col-3">tags</label>
                            <div class="col-9">
                                <input type="text" id="annotationedittagsval" class="form-control edit-modal-input" value="start">
                            </div>
                        </div>
                       <div class="form-group row" id="annotationeditvariables" hidden>
                            <label class="col-3">variables</label>
                            <div class="col-9">
                                <input type="text" id="annotationeditvariablesval" class="form-control edit-modal-input" value="start">
                            </div>
                        </div>


                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" data-dismiss="modal" id ="annotationeditButtonSave">Save changes</button>
                    </div>
                </div>
            </div>`;
    modal.innerHTML = modalCode;

    var targetDiv = $("#contextmenu");
    targetDiv.append(modal);
    var saveButton=$("#annotationeditButtonSave");
    saveButton.click(function(){
        //write the stuff back to the model
        console.log("edit ok");
        //go over the non-hidden fields and take them
        var query = [];
        var nodePath = $('#annotationeditnodepath').text();
        var fields = {"min":"min","max":"max","start":"startTime","end":"endTime","variables":"variables","tags":"tags"};
        for (let field in fields)
        {
            let hidden = $("#annotationedit"+field).attr("hidden");
            if (!hidden)
            {
                var value = JSON.parse($('#annotationedit'+field+"val").val());
                console.log("we have "+field+value);
                var subQuery = {"browsePath":nodePath+"."+fields[field],"value":value}
                query.push(subQuery);
            }


        }
        console.log("query out",query);
        http_post("/setProperties",JSON.stringify(query),null,null,null);



    });
}





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

function context_menu_click_show(option,contextMenuIndex, optionIndex)
{
    let element = option.element;

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

    var data = option.data;
    data[element]=option.currentValue;

    console.log("switch show",data);
    context_menu_set_visible_elements(option.path,data);

    superCm.setMenuOption(contextMenuIndex, optionIndex, option);
    superCm.updateMenu(allowHorzReposition = false, allowVertReposition = false);


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
    $('#doublecheck').modal("show");
    $('#doublechecktext1').text("Deleting Annotation");
    $('#doublechecktext2').text(option.data);
    var saveButton=$("#doublecheckButtonSave");
    saveButton.click(function(){
        http_post("/_delete",JSON.stringify(option.data),null,null,null);
    });
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

    option.data[option.entry]=option.currentValue;
    var query = [{browsePath:option.modelPath+".hasAnnotation.visibleTags",value:option.data}];
    http_post('/setProperties',JSON.stringify(query), null, this, null);
    superCm.setMenuOption(contextMenuIndex, optionIndex, option);
    superCm.updateMenu(allowHorzReposition = false, allowVertReposition = false);

}

function context_menu_variable_select_click(option,contextMenuIndex, optionIndex)
{
    console.log("context_menu_variable_select_click",option);
    //make the true/false check box adjustment

    var query = {parent:option.modelPath+".selectedVariables"};
    if (option.currentValue == true)
    {
        option.currentValue = false;
        option.icon = "far fa-square";
        //remove this one
        query.remove = [option.varPath];
        //also hide a potential score renderer
        let matchingString = option.name+"_score"
        for (let variablePath of option.selectedVariables)
        {
            if (variablePath.endsWith(matchingString))
            {
                query.remove.push(variablePath);
            }
        }
    }
    else
    {
        option.currentValue = true;
        option.icon = "far fa-check-square";
        // add this one
        query.add = [option.varPath];
    }
    http_post("/_references",JSON.stringify(query),null,null,null);

    superCm.setMenuOption(contextMenuIndex, optionIndex, option);
    superCm.updateMenu(allowHorzReposition = false, allowVertReposition = false);

}


function context_menu_click_function(option)
{
    console.log("context_menu_click_function, execute " + option.data);
    http_post("/_execute",JSON.stringify(option.data),null,null,null);
    superCm.destroyMenu(); // hide it
}

function context_menu_click_pipeline(option)
{
    console.log("context_menu_click_pipeline, launch   " + option.data);
    //show the cockpit
    var query = [option.data+".cockpit"];

    http_post("_getvalue",JSON.stringify(query), null,null, function(obj,status,data,params)
    {
        if (status == 200)
        {
            console.log("data");
            var cockpit = JSON.parse(data)[0];
            launch_cockpit(cockpit);
        }
    });
    superCm.destroyMenu(); // hide it
}



function context_menu_new_annotation_click(option,contextMenuIndex, optionIndex)
{
    console.log("context menue new annotation",option.setValue);
    var query = [{browsePath:option.modelPath+".nextNewAnnotation",value:option.setValue}];
    http_post('/setProperties',JSON.stringify(query), null, this, null);
    superCm.destroyMenu();
}

function context_menu_bool_settings_click(option,contextMenuIndex, optionIndex)
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

    option.data[option.entry]=option.currentValue;
    var query = [{browsePath:option.nodePath,value:option.currentValue}];
    http_post('/setProperties',JSON.stringify(query), null, this, null);

    superCm.setMenuOption(contextMenuIndex, optionIndex, option);
    superCm.updateMenu(allowHorzReposition = false, allowVertReposition = false);

}

function context_menu_edit(option,contextMenuIndex,optionIndex)
{
    //console.log("edit"+option.data);
    //$('#annotationedit').modal('show');

    var option = option;
    superCm.destroyMenu();
    // get the children of the annotation
    http_post('/_getbranchpretty',option.data, null, this, (self,status,data,params) => {
            if (status>201)
            {
                //backend responded bad, we must set the frontend back

                console.log("context_menu_edit",status);
            }
            else
            {
                console.log("context_menu_edit ok");
                //take the data
                modal = $('#annotationedit');//.modal('show');

                var data = JSON.parse(data);
                var fields=[];
                if (data.type['.properties'].value == "time")
                {
                    //time annotations
                    $('#annotationedittitle').text("Edit Annotation")
                    $('#annotationeditnodepath').text(option.data);

                    $('#annotationeditmin').attr("hidden",true);
                    $('#annotationeditmax').attr("hidden",true);
                    $('#annotationeditstart').attr("hidden",false);
                    $('#annotationeditend').attr("hidden",false);
                    $('#annotationedittags').attr("hidden",false);

                    $('#annotationeditstartval').val(JSON.stringify(data.startTime[".properties"].value));
                    $('#annotationeditendval').val(JSON.stringify(data.endTime[".properties"].value));
                    $('#annotationedittagsval').val(JSON.stringify(data.tags[".properties"].value));

                }
                else if (data.type['.properties'].value == "threshold")
                {
                    $('#annotationedittitle').text("Edit Threshold");
                    $('#annotationeditnodepath').text(option.data);

                    $('#annotationeditmin').attr("hidden",false);
                    $('#annotationeditmax').attr("hidden",false);
                    $('#annotationeditstart').attr("hidden",true);
                    $('#annotationeditend').attr("hidden",true);
                    $('#annotationedittags').attr("hidden",false);

                    $('#annotationeditminval').val(JSON.stringify(data.min[".properties"].value));
                    $('#annotationeditmaxval').val(JSON.stringify(data.max[".properties"].value));
                    $('#annotationedittagsval').val(JSON.stringify(data.tags[".properties"].value));
                }
                else
                {
                    console.log("unsupported tag type");
                    return;
                }

                modal.modal('show');


            }
        });



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
        icon: 'fa fa-edit',   //Icon for the option
        label: 'edit',   //Label to be displayed for the option
        data: data.hasAnnotation.selectedAnnotations[".properties"].leaves,
        action : function(option, contextMenuIndex, optionIndex){context_menu_edit(option,contextMenuIndex,optionIndex);},
        disabled: disableDirectModification
    },

    {
        separator : true
    }];


    //now comes the show/hide submenu
    /*
    let annotationsAction = "show";
    if (data.visibleElements[".properties"].value.annotations == true) annotationsAction = "hide";
    let backgroundAction = "show";
    if (data.visibleElements[".properties"].value.background == true) backgroundAction = "hide";
    let thresholdAction = "show";
    if (data.visibleElements[".properties"].value.thresholds == true) thresholdAction = "hide";
    let scoresAction = "show";
    if (data.visibleElements[".properties"].value.scores == true) scoresAction = "hide";
    */

    var visibleTags = data.hasAnnotation.visibleTags[".properties"].value;
    var colors = data.hasAnnotation.colors[".properties"].value;

    // for switching on and off the annotation tags
    let annotationsSubmenu = [];
    for (tag in visibleTags)
    {
        let icon = "far fa-square";
        if (visibleTags[tag]== true) {icon = "far fa-check-square";}
        let mycolor = colors[tag].color;
        let mypattern = colors[tag].pattern;
        if (mypattern == null) mypattern = "&nbsp &nbsp &nbsp";
        else mypattern = "&nbsp "+mypattern + " &nbsp";
        let mycolorString = `<span style='background-color:${mycolor};text-color:red;font-family:monospace'> <font color='white'> ${mypattern}</font> </span> &nbsp ${tag}`;
        //let mycolorString = `${tag} &nbsp <span style='textcolor:red;background-color:${mycolor}'> ${mypattern}  </span>`;

        var entry = {
            icon:icon,
            label:mycolorString,
            entry:tag,
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


    var showSubmenu = [];
    let elements = ["annotations","background","thresholds","scores","motifs"];
    var jsonValue = data.visibleElements[".properties"].value;
    for (let element of elements)
    {
        let icon = "far fa-square";
        let visible = jsonValue[element];
        if (visible == true) icon = "far fa-check-square";

        var entry = {
            icon: icon,
            label:element,
            element : element,
            path : modelPath,
            data : jsonValue,
            currentValue : visible,
            action: function(option, contextMenuIndex, optionIndex){
                        var opt = option;
                        var idx = contextMenuIndex; var
                        optIdx = optionIndex;
                        context_menu_click_show(opt,idx,optIdx);
                    }
        };
        if (element == "annotations")
        {
            entry.submenu = annotationsSubmenu;
        }
        showSubmenu.push(entry);
    }

    //another entry for the variables
    var variablesSubmenu=[];
    var selectableVariables = data.selectableVariables[".properties"].leaves;
    var selectedVariables = data.selectedVariables[".properties"].leaves;
    for (variable of selectableVariables)
    {
        let icon = "far fa-square";
        var currentValue = false;
        if (selectedVariables.includes(variable)) {icon = "far fa-check-square";currentValue =true; }
        //let mycolor = colors[tag].color;
        //let mypattern = colors[tag].pattern;
        //if (mypattern == null) mypattern = "&nbsp &nbsp &nbsp";
        //else mypattern = "&nbsp "+mypattern + " &nbsp";
        //let mycolorString = `<span style='background-color:${mycolor};text-color:red;font-family:monospace'> <font color='white'> ${mypattern}</font> </span> &nbsp ${tag}`;

        var splitted = variable.split('.');
        var name =splitted[splitted.length-1];


        var entry = {
            icon:icon,
            label:name,
            name:name,
            currentValue : currentValue,
            varPath:variable,
            selectedVariables:selectedVariables,
            modelPath:modelPath,
            action: function(option, contextMenuIndex, optionIndex){
                    var opt = option;
                    var idx = contextMenuIndex; var
                    optIdx = optionIndex;
                    context_menu_variable_select_click(opt,idx,optIdx);
                }

        }
        variablesSubmenu.push(entry);
    }
     var entry = {
            //icon: icon,
            label:"variables",
            submenu:variablesSubmenu
        };
    showSubmenu.push(entry);




    //add the show/hide to the menu
    menu.push({
        disabled: false,
        icon: 'fas fa-eye',
        label: 'show/hide',
        submenu: showSubmenu
        });




    //the "new area"

    // new annotation submenu
    let newAnnnotationsSubmenu = [];
    for (tag in visibleTags)
    {
        let mycolor = colors[tag].color;
        let mypattern = colors[tag].pattern;
        if (mypattern == null) mypattern = "&nbsp &nbsp &nbsp";
        else mypattern = "&nbsp "+mypattern + " &nbsp";
        //let mycolorString = `${tag} &nbsp <span style='background-color:${mycolor}'> ${mypattern} </span>`;
        let mycolorString = `<span style='background-color:${mycolor};text-color:red;font-family:monospace'> <font color='white'> ${mypattern}</font> </span> &nbsp ${tag}`;

        var entry = {
            label:mycolorString,
            data:visibleTags,
            modelPath:modelPath,
            setValue:{type:"time",tag:tag},
            action: function(option, contextMenuIndex, optionIndex){
                    var opt = option;
                    var idx = contextMenuIndex;
                    var optIdx = optionIndex;
                    context_menu_new_annotation_click(opt,idx,optIdx);
                }
        }

        newAnnnotationsSubmenu.push(entry);
    }

    let newThresholdsSubmenu = [];
    //selected variables?
    //let selectedVariables = data.selectedVariables[".properties"].leaves;
    let scoreVariables = data.scoreVariables[".properties"].leaves;

    let currentColors = data.currentColors[".properties"].value;
    for (variable of selectedVariables)
    {
        if (scoreVariables.includes(variable))
        {
            //skip score variables
            continue;
        }
        if (variable in currentColors)
        {
            var mycolor = currentColors[variable].lineColor;
        }
        else
        {
            var mycolor = "black";
        }
        let mycolorString = `<span style='background-color:${mycolor};text-color:red;font-family:monospace'> <font color='white'> &nbsp - &nbsp </font> </span> &nbsp ${variable}`;

        var entry = {
            label:mycolorString,
            setValue:{type:"threshold",variable:variable},
            modelPath:modelPath,
            action: function(option, contextMenuIndex, optionIndex){
                    var opt = option;
                    var idx = contextMenuIndex; var
                    optIdx = optionIndex;
                    context_menu_new_annotation_click(opt,idx,optIdx);
                }
        }

        newThresholdsSubmenu.push(entry);
    }


    let newMotifSubmenu = [];
    //selected variables?
    //let selectedVariables = data.selectedVariables[".properties"].leaves;
    //let scoreVariables = data.scoreVariables[".properties"].leaves;

    //let currentColors = data.currentColors[".properties"].value;
    for (variable of selectedVariables)
    {
        if (scoreVariables.includes(variable))
        {
            //skip score variables
            continue;
        }
        if (variable in currentColors)
        {
            var mycolor = currentColors[variable].lineColor;
        }
        else
        {
            var mycolor = "black";
        }
        let mycolorString = `<span style='background-color:${mycolor};text-color:red;font-family:monospace'> <font color='white'> &nbsp - &nbsp </font> </span> &nbsp ${variable}`;

        var entry = {
            label:mycolorString,
            setValue:{type:"motif",variable:variable},
            modelPath:modelPath,
            action: function(option, contextMenuIndex, optionIndex){
                    var opt = option;
                    var idx = contextMenuIndex; var
                    optIdx = optionIndex;
                    context_menu_new_annotation_click(opt,idx,optIdx);
                }
        }

        newMotifSubmenu.push(entry);
    }







    var menuNew = [
        {separator :true},

        {
            icon: 'fa fa-plus',
            label: 'new',
            disabled: false,
            submenu: [
                {
                    icon: 'far fa-bookmark',
                    label:"annotation",
                    submenu: newAnnnotationsSubmenu
                },
                {
                    icon: 'fas fa-arrows-alt-v',
                    label: 'threshold',
                    submenu: newThresholdsSubmenu
                },
                {
                    icon : 'fas fa-water',
                    label : 'motif',
                    submenu:newMotifSubmenu
                }
            ]
        }
    ]
    menu=menu.concat(menuNew);


    //user functions
    var menuUserFunctions =[{
            separator: true
        }];

    for (fkt of data.contextMenuFunctions[".properties"].targets)
    {
        var splitted = fkt.split(".");
        var entry={
            icon: 'fas fa-play-circle',
            label: '<font size="3" color="#d9b100">'+splitted[splitted.length -1]+'</font>',
            data: fkt,
            action: function(option, contextMenuIndex, optionIndex){context_menu_click_function(option); }
        };
        menuUserFunctions.push(entry);
    }
    if ("contextMenuPipelines" in data)
    {
        for (pipeline of data.contextMenuPipelines[".properties"].targets)
        {
            var splitted = pipeline.split(".");
            var entry={
                icon: 'fas fa-gamepad',
                label: '<font size="3" color="#d9b100">'+splitted[splitted.length -1]+'</font>',
                data: pipeline,
                action: function(option, contextMenuIndex, optionIndex){context_menu_click_pipeline(option); }
            };
            menuUserFunctions.push(entry);
        }
    }
    if (menuUserFunctions.length>1)
    {
        menu=menu.concat(menuUserFunctions);
    }




    let tailSubMenu =[];

    // y scale
    for (let child in data.contextMenuSettings)
    {
        //console.log(entry);
        if (child == ".properties") continue; // ignore this entry
        var entryPath = data.contextMenuSettings[child][".properties"].leaves[0];
        var value = data.contextMenuSettings[child][".properties"].leavesValues[0];
        var validation = data.contextMenuSettings[child][".properties"].leavesValidation[0];
        console.log(child + " > " + entryPath+ ":"+value);

        let icon = "far fa-square";
        if (value == true) icon = "far fa-check-square";

        var entry = {
            label:child,
            icon:icon,
            currentValue:value,
            nodePath:entryPath,
            data:data,
            action: function(option, contextMenuIndex, optionIndex){
                    var opt = option;
                    var idx = contextMenuIndex;
                    var optIdx = optionIndex;
                    context_menu_bool_settings_click(opt,idx,optIdx);
                }
        }

        tailSubMenu.push(entry);
    }


    var menuTail = [
        {
            separator: true
        },
        {
            icon: 'fas fa-cog',
            label : "settings",
            disabled : false,
            submenu:tailSubMenu

        },
        /*
        {
            icon: 'fas fa-bug',
            label : "debug",
            disabled : false,
            action:function(opt,idx,optIdx){
                //my_test_insert();

            }

        }
        */
    ];

    menu = menu.concat(menuTail);
    return menu;
}



function launch_cockpit(url)
{
    var data=http_get(url);


    $("#cockpit").remove();
    $("#cockpitplaceholder").html(data);

    var cockpit = $('#cockpit');
    cockpit.draggable({handle: ".modal-header"});                                   //make it movable
    cockpit.modal({backdrop: 'static',keyboard: false, focus:false});               //don't close it on click outside
    cockpit.prepend('<style scoped> .modal-backdrop { display: none;}</style>');    //allow click outside
    cockpit.attr("path","root.Motif Miner");
    cockpit_init("root.Motif Miner");

    $('#cockpit').on('hidden.bs.modal', cockpit_close);
    cockpit.modal('show');

}

/* move this to cockpit widget later
*/



$( document ).ready(function() {
    console.log( "ready!" );
    on_first_load();
});



