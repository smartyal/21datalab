/*
 the TreeWidget is the fully capable tree, can be adjusted with the settings
 the TreeWidget only cares about the tree itself, the control and layout comes from the TreeCard class
*/
class TreeWidget
{
    constructor (treeDivId,settings)
    {
        // we need to make another div in which we produce the js_tree() as this must stay completely under
        // the control of the js_Tree lib

        this.treeDivId = treeDivId;

        this.defaultSettings = {"treeRoot":"root"};
        this.settings = this.defaultSettings;
        this.settings = Object.assign(this.defaultSettings, settings); //merge the user settings into the settings

        this.templates = null; // global list with available templates
        this.treeNodes = {} ; //empty object
        this.diffHandle = null;   //the handle for the differential updates
        this.periodicTreeUpdate = false; //
        this.treeRootId = '1'; //default is the "root"
        this.globalCopyBuffer = [];
        this.globalIconType = "standard"; // use to ingest html styles for the icons
        this.treeIcons = {
            //https://fontawesome.com/icons
            root : "fa fa-folder fa-sm",
            root : "far fa-folder tree-icon-class",
            folder : "far fa-folder tree-icon-class",
            variable:"fas fa-random tree-icon-class",
            timeseries : "fas fa-chart-line fa-xs tree-icon-class",
            table :"fas fa-table tree-icon-class",
            annotation: "fas fa-pencil-alt tree-icon-class",
            widget : "fas fa-chart-line fa-xs tree-icon-class",
            column :"fas fa-columns tree-icon-class",
            const :  "fas fa-sliders-h tree-icon-class",
            referencee : "fas fa-link tree-icon-class",
            function : "fa fa-play-circle tree-icon-class",
            referencer : "fas fa-share tree-icon-class",
            reference : "fa fa-link tree-icon-class",
            template : "fa fa-file-text-o tree-icon-class",
            add : "fas fa-plus tree-icon-class",
            delete : "far fa-trash-alt tree-icon-class",
            rename : "fas fa-pencil-alt tree-icon-class",
            changevalue : "fas fa-edit tree-icon-class",
            execute : "fa fa-play tree-icon-class",
            abort : "fa fa-stop tree-icon-class",
            file:"far fa-file-alt tree-icon-class",
            copy:"far fa-copy tree-icon-class",
            paste: "fas fa-paint-roller tree-icon-class",
            toolbox: "fas fa-toolbox tree-icon-class",
            unknown: "fas fa-question-circle tree-icon-class"
        };

        var treeWidgetObject = this; //for usage in deeper object nesting

    }

    start_periodic_tree_update()
    {
        this.periodicTreeUpdate = true;
        window.setTimeout(() => {
            this.trigger_tree_update();
        }, 1000);
    }

    stop_periodicTreeUpdate()
    {
        this.periodicTreeUpdate = false;
    }

    trigger_tree_update()
    {
        if (this.periodicTreeUpdate == true)
        {
            this.tree_update();
            window.setTimeout(() => {
                this.trigger_tree_update();
            }, 1000);
        }
    }

    load_tree(name)
    {
        http_post('/_load',name, null, this, (obj,status,data,params) => {
            if (status!=200)
            {
                console.log("cant load  model"+name);
            }
            else
            {
                obj.tree_initialize();
            }
        });
    }

    save_tree(name)
    {
        http_post('/_save',name, null, null, null);
    }

    //generate all html modals needed for the tree
    make_edit_modal()
    {
        var modal = document.createElement('div');
        modal.id = this.treeContainerId+"-editNodeModal";
        modal.className = "modal fade";
        modal.setAttribute("tabindex","-1");
        modal.setAttribute("role","dialog");
        modal.setAttribute("aria-labelledby","myModalLabel");
        var modalCode = `
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h4 class="modal-title" id="myModalLabel">Edit Node Value</h4>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                        </div>
                        <div class="modal-body">
                            <div class="form-group">
                                <label id="editNodeModalName">nodePath</label>
                                <label id="editNodeModalId" hidden>id</label>
                                <input type="email" class="form-control" id="editNodeModalValue" aria-describedby="emailHelp" >
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" data-dismiss="modal" id ="editNodeModalButtonSave">Save changes</button>
                        </div>
                    </div>
                </div>`;

        modalCode = modalCode.replace('editNodeModalButtonSave',this.treeContainerId+'-editNodeModalButtonSave');
        modalCode = modalCode.replace('editNodeModalValue',this.treeContainerId+'-editNodeModalValue');
        modalCode = modalCode.replace('editNodeModalName',this.treeContainerId+'-editNodeModalName');
        modalCode = modalCode.replace('editNodeModalId',this.treeContainerId+'-editNodeModalId');

        modal.innerHTML = modalCode;
        return modal;
    }

    make_advanced_edit_modal()
    {
        var modal = document.createElement('div');
        modal.id = this.treeContainerId+"-advancedEditModal";
        modal.className = "modal fade";
        modal.setAttribute("tabindex","-1");
        modal.setAttribute("role","dialog");
        modal.setAttribute("aria-labelledby","advancedEditModalLabel");
        var modalCode = `
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h4 class="modal-title" id="advancedEditModalLabel">Edit Node Type</h4>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    </div>
                    <div class="modal-body" id="advancedEditModalBody">
                        <div class="form-group">
                            <label id="advancedEditModalName">nodePath</label>
                            <label id="advancedEditModalId" hidden>id</label>
                            <input type="email" class="form-control" id="advancedEditModalValue" aria-describedby="emailHelp" >
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-secondary" id="advancedEditModalButtonAddPropery">Add Property</button>
                        <button type="button" class="btn btn-primary" data-dismiss="modal" id ="advancedEditModalButtonSave">Save changes</button>
                    </div>
                </div>
            </div>`;

        modalCode = modalCode.replace('advancedEditModalBody',this.treeContainerId+'-advancedEditModalBody');
        modalCode = modalCode.replace('advancedEditModalButtonSave',this.treeContainerId+'-advancedEditModalButtonSave');
        modalCode = modalCode.replace('advancedEditModalButtonAddPropery',this.treeContainerId+'-advancedEditModalButtonAddPropery');

        modal.innerHTML = modalCode;
        return modal;
    }

    tree_initialize()
    {
        var treeInner = document.createElement("div");
        treeInner.id = this.treeDivId+"-treeInner";

        $("#"+this.treeDivId).append(treeInner);

        this.treeContainerId = this.treeDivId; // to append the modals or any other
        this.treeDiv = "#"+this.treeDivId+"-treeInner"; //the js_tree controls this div completely


        $(this.treeDiv).jstree(); //make the divs and scripts
        this.tree_generate();


        //bring in the modals
        var editModal = this.make_edit_modal();
        $("#"+this.treeContainerId).append(editModal);
        var advancedEditModal = this.make_advanced_edit_modal();
        $("#"+this.treeContainerId).append(advancedEditModal);
        //hook the callbacks


        //get the templates
        var data = http_get('/templates');
        try
        {
            this.templates = JSON.parse(data);
        }
        catch(err)
        {
            return;
        }

        $(this.treeDiv).on("select_cell.jstree-grid", (e,data) => {
            //alert( "The user double clicked a jstreegrid cell"+data.column+"  "+data.value+ );
            var id = data.node.get()[0].id;
            var value = this.treeNodes[id].value;
            //we only edit variables, consts
            if ( (this.treeNodes[id].type == "variable") || (this.treeNodes[id].type == "const") )
            {
                //only vars and consts can be edited
                $('#'+this.treeContainerId+'-editNodeModalName').text(this.treeNodes[id].browsePath);
                $('#'+this.treeContainerId+'-editNodeModalValue').val(JSON.stringify(this.treeNodes[id].value));
                $('#'+this.treeContainerId+'-editNodeModalId').val(id);
                $('#'+this.treeContainerId+'-editNodeModal').modal('show');
            }
        });

        $('#'+this.treeContainerId+'-editNodeModalButtonSave').click( () => {
            var id = $('#'+this.treeContainerId+'-editNodeModalId').val();
            var value = JSON.parse($('#'+this.treeContainerId+'-editNodeModalValue').val());
            var query=[{"id":id,"value":value}];
            http_post("/setProperties",JSON.stringify(query),null,null,null);
        });

        $('#'+this.treeContainerId+'-advancedEditModalButtonSave').click(() => {
            // var id = $('#advancedEditModalId').val();
            // var value = JSON.parse($('#advancedEditModalValue').val());
            // var query=[{"id":id,"type":value}];
            // http_post("/setProperties",JSON.stringify(query),null,null,null);

            let params = {
                id: $('#'+this.treeContainerId+'-advancedEditModalBody').attr('data-node-id')
            }

            $('#'+this.treeContainerId+'-advancedEditModalBody').find('.form-group').each((index, el) => {
                // Get the propery id corresponding to this row in the form
                let paramKey = $(el).attr("data-property-id");
                // In case it doesn't have one it means it was a new set of property key value pair
                if (paramKey != undefined) {
                    let paramValue = $('input', el).val();
                    params[paramKey] = paramValue;
                }
                else {
                    // Get the propery id from the
                    paramKey = $('.property-id', el).val();
                    let paramValue = $('.property-value', el).val();
                    params[paramKey] = paramValue;
                }
            });

            console.log(params);

            http_post("/setProperties",JSON.stringify([params]),null,null);
        });

        $('#'+this.treeContainerId+'-advancedEditModalButtonAddPropery').click((event) => {
            let row = $(`<div class="form-group row">
                <div class="col-5">
                    <input type="text" class="form-control property-id" value="">
                </div>
                <div class="col-5">
                    <input type="text" class="form-control property-value" value="">
                </div>
                <div class="col-2">
                    <div class="card-header-actions">
                        <a class="card-header-action delete-property" data-toggle="tooltip" data-placement="top" title="Delete property">
                            <i class="fas fa-trash-alt"></i>
                        </a>
                    </div>
                </div>
            </div>`)

            $('.delete-property', row).click((event) => {
                let formGroupRow = event.target.closest(".form-group");
                // let propertyID = $(formGroupRow).attr("data-property-id");
                $(formGroupRow).remove();
            });

            $('#'+this.treeContainerId+'-advancedEditModalBody').append(row);
        });

    }

    get_id_from_browse_path(browsePath)
    {
        for (var nodeid in this.treeNodes)
        {
            var node = this.treeNodes[nodeid]
            if (node.browsePath == browsePath)
            {
                return node.id;
            }
        }
        return null;
    }


    tree_generate()
    {
        var treeWidgetObject = this; //for usage in deeper object nesting

        $(this.treeDiv).jstree("destroy");
        //data = http_get("/_getall");
        var data = http_get("_diffUpdate"); //the diff update call without data return a handle and the full model

        try
        {
            var parsed = JSON.parse(data);
            var model = parsed.model;
            this.diffHandle = parsed.handle; //this is a global
        }
        catch(err)
        {
            return;
        }

        this.treeNodes = model; //keep a copy in the global

        //find the tree root node id
        this.treeRootId = this.get_id_from_browse_path(this.settings.treeRoot);


        var nodes = this.create_children(model,this.treeRootId);


        // Depending on the global theme set the default or the default-dark as the tree theme
        let themeToUse = "default";
        if (datalabGlobalTheme == "dark") {
            themeToUse = "default-dark";
            // Overwrite the jstree grid header colors
            $("<style>")
                .prop("type", "text/css")
                .html(`.jstree-grid-header-regular {
                    background-color: #444 !important;
                }`)
                .appendTo("head");
        }
        var myTree = {
            'plugins':["grid", "contextmenu","types","dnd"],
            'core': {
                "themes" : {
                    "variant": "small",
                    "name": themeToUse
                },
                'data': [
                     {
                        'text': ' '+this.settings.treeRoot,
                        'state': {
                            "opened": true,
                            "selected": false
                        },
                        'id': this.treeRootId,
                        'modelId': this.treeRootId,
                        'type': this.globalIconType,
                        'icon':this.treeIcons["root"],
                        'children': nodes,
                        data: {}
                    }
                ],
                'check_callback' : function(operation, node, node_parent, node_position, more) {
                    console.log('check_callback ' + operation + " " + node.id + " " +node.text+ "parent"+node_parent.text);
                    if (operation === "move_node")
                    {
                        // if the move has actually taken place, we allow the tree to finish it
                        if (nodesMoving.vakata == "stopped") return true;

                        //the check callback will be called again when we execute the moving, not only during drop, so the "more" might not
                        // be there on the second cyll
                        try
                        {
                                console.log("jstree.check_callback/move_node:",node.id,"from",node.parent,"=>",node_parent.id,"pos",node_position,"more",more.ref.text);
                                nodesMoving.newParent = more.ref.id; //store this info for the later execution of the move
                        }
                        catch{}

                        // This is called when drag and drop action is performed inside the tree
                        // Handle the logic which determines if the source node can be dragged on the destination
                        // we always return false here; if we return true then the tree will do moves by itself, so we can't avoid
                        // movings into referencers etc. the actual move will be done inside the dnd_stop.vakata
                        return false;
                    }
                    return true; //we allow all operations as default
                }
            },
            'grid': {
                columns: [
                    { header: "Nodes" },
                    { header: "Value", value:"value"}
                    //{ header: "Value", value:"value"}function(node){return(node.data.value);
                ]
            },
            'contextmenu':{
                items: function(node){
                    var menuObject={
                        "delete": {
                            "label": "delete",
                            "action": function (obj) {treeWidgetObject.context_menu_delete(node);},
                            "icon": treeWidgetObject.treeIcons["delete"]
                        }
                    };

                    //creation is only for non-referencer
                    if ((node.id in treeWidgetObject.treeNodes) && (treeWidgetObject.treeNodes[node.id].type != "referencer"))
                    {
                        menuObject["create"]={
                            "label":"new",
                            "icon":treeWidgetObject.treeIcons["add"],
                            "submenu":
                            {
                                "node":
                                {
                                    "label":"node",
                                    "submenu":
                                    {
                                        "folder":
                                        {
                                            "label":"folder",
                                            "action":function(obj){treeWidgetObject.context_menu_create(node,"folder");},
                                            "icon":treeWidgetObject.treeIcons["folder"]
                                        },
                                        "variable":
                                        {
                                            "label":"variable",
                                            "action":function(obj){treeWidgetObject.context_menu_create(node,"variable");},
                                            "icon":treeWidgetObject.treeIcons["variable"]
                                        },
                                        "const":
                                        {
                                            "label":"const",
                                            "action":function(obj){treeWidgetObject.context_menu_create(node,"const");},
                                            "icon":treeWidgetObject.treeIcons["const"]
                                        },
                                        "file":
                                        {
                                            "label":"file",
                                            "action":function(obj){treeWidgetObject.context_menu_create(node,"file");},
                                            "icon":treeWidgetObject.treeIcons["file"]
                                        },
                                        "referencer":
                                        {
                                            "label":"referencer",
                                            "action":function(obj){treeWidgetObject.context_menu_create(node,"referencer");},
                                            "icon":treeWidgetObject.treeIcons["referencer"]
                                        },
                                        "column":
                                        {
                                            "label":"column",
                                            "action":function(obj){treeWidgetObject.context_menu_create(node,"column");},
                                            "icon":treeWidgetObject.treeIcons["column"]
                                        }
                                    }
                                },
                                "template":
                                {
                                    "label":"template",
                                    "submenu":{}
                                }
                            }
                        }
                        // now make the templates entries
                        for (let template of treeWidgetObject.templates)
                        {
                            //var template = templ
                            var entry = {
                                "label":template,
                                "__templateType":template, //to store it here, so we get it back on the call
                                "action":function(obj){treeWidgetObject.context_menu_create_template(node,obj.item.__templateType);}
                            }
                            menuObject.create.submenu.template.submenu[template]=entry;

                        }
                    }

                    //if treeWidgetObject node is a function, execution is also possible
                    if ((node.id in treeWidgetObject.treeNodes) && (treeWidgetObject.treeNodes[node.id].type == "function"))
                    {

                        menuObject["execute"] = {
                            "label": "execute",
                            "action": function(obj){treeWidgetObject.context_menu_execute(node);},
                            "icon": treeWidgetObject.treeIcons["function"]
                        }
                    }

                    //if treeWidgetObject node is not a referencee node, renaming is possible
                    if ((node.original.nodeType != "referencee"))
                    {

                        menuObject["rename"] = {
                            "label": "rename",
                            "action": function(obj){treeWidgetObject.context_menu_rename(node);},
                            "icon": treeWidgetObject.treeIcons["rename"]
                        }
                    }

                    // for variables and const also editing is possible
                    if ((node.original.nodeType == "variable") || (node.original.nodeType == "const"))
                    {
                        menuObject["editvalue"] ={
                            "label" : "edit value",
                            "action" : function(obj){treeWidgetObject.context_menu_change_value(node);},
                            "icon": treeWidgetObject.treeIcons["changevalue"]
                        }
                    }


                    //if all selected nodes are not referencees, then copy is possible
                    var allNodes = $(treeWidgetObject.treeDiv).jstree(true).get_selected();
                    var isReferencee=false;
                    for (let nodeId of allNodes)
                    {
                        var node = $(treeWidgetObject.treeDiv).jstree(true).get_node(nodeId);
                        if (node.original.nodeType == "referencee")
                        {
                            isReferencee = true;
                            break;
                        }
                    }
                    if (isReferencee == false)      // only if none of the selected is areferencee are we able to copy
                    {
                        menuObject["copy"] = {
                            "label": "copy",
                            "action": function(obj){treeWidgetObject.context_menu_copy(node);},
                            "icon": treeWidgetObject.treeIcons["copy"]
                        }
                    }

                    //for referencees, paste is possible
                    if (node.original.nodeType == "referencer")
                    {
                        menuObject["paste"] = {
                            "label": "paste",
                            "action": function(obj){treeWidgetObject.context_menu_paste(node);},
                            "icon": treeWidgetObject.treeIcons["paste"]
                        }
                    }

                    //advanced menu
                    menuObject["advanced"] = {
                        "label":"advanced",
                        "icon": treeWidgetObject.treeIcons["toolbox"],
                        "submenu":{
                            "edit properties":{
                                "label":"edit properties",
                                "icon":treeWidgetObject.treeIcons["changevalue"],
                                "action":function(obj){treeWidgetObject.context_menu_change_properties(node);}
                            }
                        }
                    }
                    return menuObject;
                }
            },
            'types':{
                // "standard":{"a_attr":{"style":"color:#606060;background-color:white"}},
                // "inverse":{"a_attr":{"style":"color:white;background-color:grey"}},
                // Commented the above lines because it was overwriting the default and the default-dark themes colors and backgrounds
                "standard":{},
                "inverse":{}
            },
            'dnd' : {
                "check_while_dragging": true,
                "inside_pos": "last"
            }

        }

        $(this.treeDiv).jstree(myTree);

        /*
        // Register a callback for the node move event inside the tree
        $(this.treeDiv).on("move_node.jstree", function(e, data) {
            // This event is triggered when a node is dropped on another node inside the tree
            // and initial check from the check callback returned true
            // when we are here,the move HAS BEEN performed by the jstree already, so we do is elsewhere:
            // in the dnd_stop.vakata
            return false;
        });
        */
    }

    context_menu_change_properties(node)
    {
        var id = node.id;
        var modelNode = this.treeNodes[id];

        $('#'+this.treeContainerId+'-advancedEditModalBody').empty();

        $('#'+this.treeContainerId+'-advancedEditModalBody').attr("data-node-id", id)

        // Go over the properties of the node and create a form with all the properties that can be edited
        let keysToIgnore = ["id", "browsePath", "children", "parent", "forwardRefs", "backRefs", "value"];

        for (let key in modelNode) {
            if (keysToIgnore.indexOf(key) == -1) {
                console.log("Create entry for: " + key);

                $('#'+this.treeContainerId+'-advancedEditModalBody').append(
                    `<div class="form-group row" data-property-id="` + key + `">
                        <label class="col-5"> ` + key + `</label>

                        <div class="col-5">
                            <input type="text" class="form-control" value="` + modelNode[key] + `">
                        </div>
                        <div class="col-2">
                            <div class="card-header-actions">
                                <a class="card-header-action delete-property" data-toggle="tooltip" data-placement="top" title="Delete property">
                                    <i class="fas fa-trash-alt"></i>
                                </a>
                            </div>
                        </div>
                    </div>`);
            }
        }

        $('.delete-property').click((event) => {
            let formGroupRow = event.target.closest(".form-group");
            // let propertyID = $(formGroupRow).attr("data-property-id");
            $(formGroupRow).remove();
        });

        $('#' + this.treeContainerId + "-advancedEditModal").modal('show');
    }

    context_menu_delete(node)
    {
        console.log("context delete",node);
        //deleting is different for referencee nodes, these are in fact references
        var allNodes = $(this.treeDiv).jstree(true).get_selected();
        //http_post("/_delete",JSON.stringify(allNodes),null,null,null);

        //now for the referencees here, we remove the refs
        var allRefs={}; //all refs holds the parent:[list of references o delete]
        var allNormalNodes = []; //list of al normal nodes to delete

        for (let nodeId of allNodes)
        {
            var node = $(this.treeDiv).jstree(true).get_node(nodeId);
            if (node.original.nodeType == "referencee")
            {
                if (!(allRefs.hasOwnProperty(node.parent)))
                {
                    allRefs[node.parent]=[];
                }

                allRefs[node.parent].push(node.original.targetId);
            }
            else
            {
                //this is a standard node to delete
                allNormalNodes.push(nodeId);
            }
        }

        //now delete normal nodes
        if (Object.keys(allNormalNodes).length != 0)
        {
            http_post("/_delete",JSON.stringify(allNormalNodes),null,null,null);
        }

        //we must delete some references
        if (Object.keys(allRefs).length !=0)
        {
            for (let parent in allRefs)
            {
                var query={"parent":parent,"remove":allRefs[parent]};
                http_post("/_references",JSON.stringify(query),null,null,null);
            }
        }
    }

    context_menu_execute(node)
    {
        console.log("context execute",node);
        var query=node.id;
        http_post("/_execute",JSON.stringify(query),null,null,null);
    }

    context_menu_create_template(node,templateType)
    {
        console.log("create template",node,templateType);
        var splitted = templateType.split('.');
        var templateName = splitted.pop();
        var newBrowsePath = this.treeNodes[parseInt(node.id)].browsePath+".new_"+templateName+"_"+Math.random().toString(16).substring(2,6);
        var query={"type":templateType,"browsePath":newBrowsePath};
        http_post('/_createTemplate',JSON.stringify(query),null,null,null);
    }

    context_menu_rename(node)
    {
        //$(this.treeDiv).jstree(true).edit(node,null,this.edit_node_done);
        $(this.treeDiv).jstree(true).edit(node,null, (node,status,cancel) => {
            this.edit_node_done(node,status,cancel);
        });
    }

    context_menu_create(node,type)
    {
        var newBrowsePath = this.treeNodes[parseInt(node.id)].browsePath+".new_"+type+"_"+Math.random().toString(16).substring(2,6);
        var query=[{"browsePath":newBrowsePath,"type":type}];
        console.log("create ",newBrowsePath);
        http_post('/_create',JSON.stringify(query),node,null);
    }

    context_menu_copy(node)
    {

        var allNodes = $(this.treeDiv).jstree(true).get_selected();
        this.globalCopyBuffer = allNodes;
        console.log("context_menu_copy ",allNodes);

    }

    context_menu_paste(node)
    {
        console.log("paste",node,this.globalCopyBuffer);
        //if type(this.globalCopyBuffer)
        var query={"parent":node.id,"add":this.globalCopyBuffer};
        http_post("/_references",JSON.stringify(query),null,null);
    }

    context_menu_change_value(node)
    {
            var id = node.id;
            var value = this.treeNodes[id].value;
            //only vars and consts can be edited
            $('#'+this.treeContainerId+'-editNodeModalName').text(this.treeNodes[id].browsePath);
            $('#'+this.treeContainerId+'-editNodeModalValue').val(JSON.stringify(this.treeNodes[id].value));
            $('#'+this.treeContainerId+'-editNodeModalId').val(id);
            $('#'+this.treeContainerId+'-editNodeModal').modal('show');
    }

    edit_node_done(node, status, cancel)
    {
        // we check if the new name is allowed: it must be unique under the parent
        console.log("edit node done",status,cancel);

        var children = this.treeNodes[parseInt(node.parent)].children;
        var originalName = this.treeNodes[parseInt(node.id)].name;
        var newName = node.text;

        if ((newName == originalName)  ||  (cancel == true))
        {
            //still the old name, nothing to do
            console.log("old name,nothing to do, cancel ");
            return ;
        }

         //iterate over the children
        for (let child in children)
        {
            var brotherName = this.treeNodes[parseInt(children[child])].name;
            if (brotherName == newName)
            {
                //not allowed , bring back the old name
                $(this.treeDiv).jstree(true).rename_node(node,originalName);
                console.log("not allowed name exist under parent");
                return;
            }
        }
        var query=[{id:node.id,name:newName}];
        var params={id:node.id,'originalName':originalName,'newName':newName};
        http_post('/setProperties',JSON.stringify(query), params, this, (self,status,data,params) => {
            if (status>201)
            {
                //backend responded bad, we must set the frontend back
                $(this.treeDiv).jstree(true).rename_node(node,params.originalName);
                console.log("renameing did not work on backend");
            }
            else
            {
                //all good, we also adjust the settings in our local view
                this.treeNodes[params.id].name=params.newName;
                this.treeNodes[params.id].browsePath = (this.treeNodes[params.id].browsePath.split('.').slice(0,-1)).join('.')+'.'+params.newName;
            }
        });

        console.log("change to new name!", newName);
    }

    //get the differential tree
    tree_update()
    {
        var query = {handle: this.diffHandle};
        http_post('/_diffUpdate/', JSON.stringify(query),null,this,(self,status,data,params) =>
        {
            if (status > 201) return;

            try
            {
                var updateData =JSON.parse(data);
                this.diffHandle = updateData.handle; //remember self for the next time
            }
            catch
            {
                return;
            }

            // remove deleted nodes from the tree
            for (let i=0;i<updateData.deletedNodeIds.length;i++)
            {
                var deleteId = updateData.deletedNodeIds[i];
                delete this.treeNodes[parseInt(deleteId)]; //remove it from the global tree
                // if the jstree does not have this node (reduced tree), the delete_node will fail with false
                var res = $(this.treeDiv).jstree().delete_node(deleteId);
                console.log("deleting id ",deleteId,res);
                // missing here is the synchronization with the self.treeNodes: the parent still holds the id in it's list,
                // this will be fixed when we look for the modifications:
                // the parent will be in the modified nodes list, finally we will take over the new node dict of the parent
            }

            // add new nodes
            for (let newNodeId in updateData.newNodes)
            {
                var node = updateData.newNodes[newNodeId];
                console.log("new node",node.id)
                var treeNode = this.node_to_tree(node);
                // if the parent is not part of the jstree, then the create will fail with return false
                $(this.treeDiv).jstree(true).create_node(node.parent, treeNode);
                this.treeNodes[newNodeId] = node; //store the nodedict info in the tree
                // missing here is the synchronization with the self.treeNodes: the parent still holds the id in it's list,
                // self will be fixed when we look for the modifications:
                // the parent will be in the modified nodes list, finally we will take over the new node dict of the parent

                // if the new node is a referencer we also must create the referencee nodes, we do self later
                // as we might reference to nodes that don't exist yet
            }

            //synchronize modified nodes
            for (let id in updateData.modifiedNodes)
            {
                var newNode = updateData.modifiedNodes[id];
                var oldNode = this.treeNodes[parseInt(id)];

                var tree = $(this.treeDiv).jstree(true);
                var treeNode = tree.get_node(id);
                if ((treeNode == 'undefined') || (treeNode == false))
                {
                    // this can happen if we have a reduced tree e.g. the treeroot that we show is not the "root" but some other branch
                    // then we do nothing but take the node in
                    this.treeNodes[id] = newNode;
                    continue;
                }

                // we will take over the full property dictionary, but we also must do some special things
                // for properties that have an importance for the front end; these are:
                // name, value, children and references
                // check if any property relevant for thehas changed

                //check name changes
                if (newNode.name != oldNode.name)
                {
                    tree.rename_node(id, newNode.name);
                }

                try
                {   //check value changes: values can be complex, so we stringify them to compare
                    if (JSON.stringify(newNode.value) != JSON.stringify(oldNode.value))
                    {
                        //trigger the redraw of the node, unfortunately all other redraw(), refresh() etc. do not trigger the grid refresh
                        treeNode.data.value = JSON.stringify(newNode.value);
                        treeNode["a_attr"]={"title":JSON.stringify(newNode.value),"class":"show_tooltip"};
                        tree.rename_node(id,newNode.name); // same name as it was, self is to trigger the redraw
                    }
                }
                catch{}

                //check type changes
                if (newNode.type != oldNode.type)
                {
                    if (newNode.type in this.treeIcons)
                    {
                        var icon = this.treeIcons[newNode.type];
                    }
                    else
                    {
                        var icon = this.treeIcons["unknown"];
                    }
                    treeNode.icon = icon;
                    tree.rename_node(id,newNode.name);// same name as it was, self is to trigger the redraw
                }


                //check modification of dependencies: children and references
                if (newNode.children.toString() != oldNode.children.toString())
                {
                    //iterate over the array
                    for (let index =0; index < newNode.children.length;index++)
                    {
                        if (newNode.children[index] != oldNode.children[index])
                        {
                            var result = $(this.treeDiv).jstree(true).move_node(newNode.children[index],newNode.id,index);
                            console.log("move ",newNode.children[index]," to parent ",newNode.id,"on position ", index,"jstreeresult:",result);
                        }
                    }
                    //children have changed
                }

                if (newNode.forwardRefs.toString() != oldNode.forwardRefs.toString())
                {
                    //references have changed, we take the brute force by rebuilding all refs from scratch
                    // for self, we iterate over the children of the referencer - js tree node
                    // we must use the real node of the jstree, as the reference - node are
                    // only create on the js tree, not in the models
                    var oldTreeNode = $(this.treeDiv).jstree(true).get_node(oldNode.id);
                    var children = oldTreeNode.children;
                    var result = $(this.treeDiv).jstree(true).delete_node(children);
                    console.log("deleted reference nodes ",children.toString()," from ",oldNode.id,"result ",result);

                    //now rebuild them
                    for (let entry in newNode.forwardRefs)
                    {
                        var targetId = newNode.forwardRefs[entry];
                        var referenceeModelNode = {
                                'type': 'referencee',
                                'name': this.treeNodes[targetId].browsePath,
                                'parent': newNode.id,
                                'targetId' : targetId //for later
                        };
                        var referenceeNode = this.node_to_tree(referenceeModelNode);
                        var result = $(this.treeDiv).jstree(true).create_node(newNode.id,referenceeNode);
                        console.log("built reference",referenceeModelNode.name,result);
                    }
                }
                this.treeNodes[id] = newNode; // update the new properties including children, refs etc
            }

            // now check if a referencer is inside the new nodes so we also need to build the referencee nodes
            for (let newNodeId in updateData.newNodes)
            {
                var node = updateData.newNodes[newNodeId];
                if (node.type == "referencer")
                {
                    for (let entry in node.forwardRefs)
                    {
                        var targetId = node.forwardRefs[entry];
                        var referenceeModelNode = {

                                'type': 'referencee',
                                'name': this.treeNodes[targetId].browsePath,
                                'parent': node.id,
                                'targetId' : targetId
                        };
                        var referenceeNode = this.node_to_tree(referenceeModelNode);
                        var treeNode = $(this.treeDiv).jstree(true).get_node(node.id);
                        let result = $(this.treeDiv).jstree(true).create_node(node.id,referenceeNode);

                    }
                }
            }
        });
    }

    //returns an array of children ready for the tree
    create_children(model,parentNodeId)
    {
        var childNodes =[];
        var childrenIds = model[parentNodeId].children;
        if (childrenIds.length>0)
        {
            for (let index in childrenIds)
            {
                var childNodeId = childrenIds[index];
                var childNode = model[childNodeId];
                var treeNode = this.node_to_tree(childNode);
                //some more stuff
                treeNode.data.nodeid=childNodeId;
                //treeNode.data['value']=childNode['value'];

                if (childNode.children.length>0)
                {
                    //this childnode has children itself, make them
                    treeNode.children = this.create_children(model,childNodeId);
                }
                else
                {
                    //no more children, but maybe this is a referecer?
                    treeNode.children=[];
                    if (childNode.type =="referencer")
                    {

                        for (let entry in childNode.forwardRefs)
                        {
                            var targetId = childNode.forwardRefs[entry];
                            var referenceeModelNode = {

                                    'type': 'referencee',
                                    'name': model[targetId].browsePath,
                                    'parent': childNode.id,
                                    'targetId' : targetId
                            };
                            var referenceeNode = this.node_to_tree(referenceeModelNode);
                            treeNode.children.push(referenceeNode);
                        }
                    }
                }
                childNodes.push(treeNode);
            }
            return childNodes;
        }
        else
        {
            return [];
        }
    }


    node_to_tree(modelNode)
    {
        //parse the model Node, we expect the parent to be there already
        if (modelNode.type in this.treeIcons)
        {
            var icon = this.treeIcons[modelNode.type];
        }
        else
        {
            var icon = this.treeIcons["unknown"];
        }

        var newTreeNode = {
                'id': modelNode.id,
                'parent': modelNode.parent,
                'type': this.globalIconType,
                'nodeType':modelNode.type,
                'text': modelNode.name,
                'state': {
                    'opened': false,
                    'selected': false
                },
                'children': [],
                'data': {},
                'icon': icon
        };
        if (modelNode.hasOwnProperty('targetId'))
        {
            newTreeNode['targetId'] = modelNode.targetId;
        }

        if ((newTreeNode.nodeType == "const")  || (newTreeNode.nodeType == "variable") || (newTreeNode.nodeType == "column"))
        {
            newTreeNode.data.value = JSON.stringify(modelNode.value);//modelNode.value;
            newTreeNode["a_attr"]={"title":JSON.stringify(modelNode.value),"class":"show_tooltip"};
        }
        return newTreeNode;
    }

}



/*
 the TreeCard class generates all necessary html dynamically to produce a card including a tree into the given div
*/
class TreeCard
{
    constructor(targetDivId,settings)
    {
        this.targetDivId = targetDivId; // the div where we place the card
        this.settings = settings;
        this.defaultSettings = {"standardButtons":["reload","update","save","saveas","load"]};
        this.settings = this.defaultSettings;
        this.settings = Object.assign(this.defaultSettings, settings); //merge the user settings into the settings


        /*
            the settings are : settings generation goes through 3 steps

            1) take the default settings into the settings of this instance
            2) if more settings are given in the constructor, we override the defaults
            3) if a widgetPath is given, we call the restserver, get settings and again overrides the settings from the model

            standardActions=["load","refresh","autorefresh","save""saveas"
            userActions={"myaction":{"icon":"fas fas folder","function":"root.function"}}
            enableCreateTypes=["folder","const"] //give a list of types or "all", "none"
            enableRenameTypes=["folder"....
            enableDeleteTypes =[...
            enableCreateTemplates = true/false
            enableCopyPaste
            enableDragAndDrop
            enableValueEdit
            showValue
            enableAutoRefreshOnStart = on/off/auto
            displayRoot = "root" or other node like "root.machine1.myvariables"

            widgetPath = "root.deployment.ui.mytree"


        */
        this.targetDiv = $("#"+this.targetDivId);
        this.instanceName = this.targetDivId+"-";

        var card = this.create_card();
        this.targetDiv.append(card);

        //now the card was created, we now also create a tree
        this.myTree = new TreeWidget(this.targetDivId+"-"+"jstree-div",this.settings);
        this.myTree.tree_initialize();

        //now start automatic updates
        this.autoUpdate = false; // we start without
        this.update_on_click(); //start the auto update

        //hook the ok buttons

        if ( $('#'+this.instanceName+'saveModelAsBtnApply') .length )
        {
            $('#'+this.instanceName+'saveModelAsBtnApply').click( () => {
                this.save_as_on_ok_click();
            });
        }

        if ( $('#'+this.instanceName+'loadModelBtnApply') .length )
        {
            $('#'+this.instanceName+'loadModelBtnApply').click( () => {
                this.load_on_ok_click();
            });
        }

    }

    get_model_name()
    {
        try
        {
            let info = http_get('/modelinfo');
            var crtModelName = JSON.parse(info).name;
            this.modelName = crtModelName;
            return crtModelName;
        }
        catch
        {
            return null;
        }
    }

    create_save_as_modal()
    {
        var modal = document.createElement('div');
        modal.id = this.instanceName+"saveModelAsModal";
        modal.className = "modal fade";
        modal.setAttribute("tabindex","-1");
        modal.setAttribute("role","dialog");
        var modalCode = `<div class="modal-dialog" role="document">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h4 class="modal-title">Save Model As</h4>
                                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                                </div>
                                <div class="modal-body">
                                    <div class="form-group">
                                        <label>Model Name</label>
                                        <input type="text" class="form-control" id="saveModelAsModelName">
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                                    <button type="button" class="btn btn-primary" data-dismiss="modal" id ="saveModelAsBtnApply">Save model</button>
                                </div>
                            </div>
                        </div>`;
        modalCode = modalCode.replace('saveModelAsModelName',this.instanceName+'saveModelAsModelName');
        modalCode = modalCode.replace('saveModelAsBtnApply',this.instanceName+'saveModelAsBtnApply');
        modal.innerHTML = modalCode;
        return modal;
    }

    create_load_modal()
    {
        var modal = document.createElement('div');
        modal.id = this.instanceName+"loadModelModal";
        modal.className = "modal fade";
        modal.setAttribute("tabindex","-1");
        modal.setAttribute("role","dialog");
        var modalCode = `<div class="modal-dialog" role="document">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h4 class="modal-title" id="myModalLabel">Load Model</h4>
                                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                                </div>
                                <div class="modal-body">
                                    <div class="form-group">
                                        <label>Model Name</label>
                                        <select class="form-control" id="modelSelect"></select>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                                    <button type="button" class="btn btn-primary" data-dismiss="modal" id ="loadModelBtnApply">Load model</button>
                                </div>
                            </div>
                         </div>`;
        modalCode = modalCode.replace('modelSelect',this.instanceName+'modelSelect');
        modalCode = modalCode.replace('loadModelBtnApply',this.instanceName+'loadModelBtnApply');
        modal.innerHTML = modalCode;
        return modal;
    }

    update_load_modal()
    {
        //get the possible models from the backend
        let data = http_get("/models");
        let models = JSON.parse(data);

        $('#'+this.instanceName+'modelSelect').empty();

        $('#'+this.instanceName+'modelSelect').append('<option value="" disabled selected>Choose a model</option>')

        for (let model of models)
        {
            $('#'+this.instanceName+'modelSelect').append(`<option>` + model + `</option>`);
        }
    }

    create_card()
    {
        // first the card header
        var cardHeader = document.createElement("div");
        cardHeader.className = "card-header";

        var span = document.createElement("SPAN");
        span.id = this.instanceName+"currentModelName";
        span.innerHTML = this.get_model_name();

        var cardHeaderActions = document.createElement("div");
        cardHeaderActions.className = "card-header-actions";

        for (let button of this.settings.standardButtons)
        {
            if (button == "reload")
            {
                var newButton = this.make_button("reloadtreebtn","reload model","fas fa-redo-alt");
                cardHeaderActions.appendChild(newButton);
                newButton.onclick = () => {this.reload_on_click();}
            }
            else if (button == "update")
            {
                var newButton = this.make_button("updatetreebtn","toggle model auto-refresh","fas fa-sync-alt");
                cardHeaderActions.appendChild(newButton);
                newButton.onclick = () => {this.update_on_click();}
            }
            else if (button == "save")
            {
                var newButton = this.make_button("saveModelBtn","save current model","fas fa-save");
                cardHeaderActions.appendChild(newButton);
                newButton.onclick = () => {this.save_on_click();}

                //we also need the modal

            }
            else if (button == "saveas")
            {
                var newButton = this.make_button("saveModelAsBtn","save current model as ...","fas fa-file-export");
                cardHeaderActions.appendChild(newButton);
                newButton.onclick = () => {this.save_as_on_click();}
                var modal = this.create_save_as_modal();
                cardHeaderActions.appendChild(modal);
            }
            else if (button == "load")
            {
                var newButton = this.make_button("loadModelBtn","load model ...","fas fa-folder-open");
                cardHeaderActions.appendChild(newButton);
                newButton.onclick = ()=>{this.load_on_click();}
                var modal = this.create_load_modal();
                cardHeaderActions.appendChild(modal);
            }
        }

        cardHeader.appendChild(span);
        cardHeader.appendChild(cardHeaderActions);

        //now the card body
        var cardBody = document.createElement("div");
        cardBody.className = "card-body";

        var treeContainer = document.createElement("div");
        // treeContainer.className = "pre-scrollable";
        treeContainer.id="jstreeContainer";
        treeContainer.setAttribute("style","overflow: auto; width: 100%;");

        var treeElement = document.createElement("div");
        treeElement.id = this.instanceName+"jstree-div";
        treeElement.className = "jstree jstree-default";
        // TODO: Make this configurable through the options maybe
        treeElement.setAttribute("style","max-height: 750px;");

        treeContainer.appendChild(treeElement);
        cardBody.appendChild(treeContainer);

        //now the whole card
        var card = document.createElement("div");
        card.className = "card";
        card.appendChild(cardHeader);
        card.appendChild(cardBody);
        return card;
    }

    make_button(id,title,icon)
    {
        var button = document.createElement("a");
        button.id = this.instanceName+id;
        button.className = "card-header-action";
        button.setAttribute("data-toggle","tooltip");
        button.setAttribute("data-placement","top");
        button.setAttribute("title",title);
        var itag = document.createElement("I");
        itag.className = icon;
        button.appendChild(itag);
        return button;
    }

    //the standard callbacks for the card header icons
    load_on_click()
    {
        console.log("load something"+this.instanceName);
        this.update_load_modal();
        $('#'+this.instanceName+"loadModelModal").modal();
    }

    load_on_ok_click()
    {
        console.log("load something"+this.instanceName);

        let modelName =  $('#'+this.instanceName+'modelSelect').val();
        this.modelName = this.myTree.load_tree(modelName);
        $('#'+this.instanceName+"currentModelName").html(modelName);
    }

    save_on_click()
    {
        this.myTree.save_tree(this.modelName);
    }

    save_as_on_click()
    {
        $('#'+this.instanceName+"saveModelAsModal").modal();
    }

    save_as_on_ok_click()
    {
        let modelName = $('#'+this.instanceName+"saveModelAsModelName").val();
        $('#'+this.instanceName+"saveModelAsModelName").val('');
        http_post('/_save', modelName, null, null,null);
        this.modelName = modelName;
        $('#'+this.instanceName+"currentModelName").html(modelName);
    }

    reload_on_click()
    {
        this.myTree.tree_initialize();
    }

    update_on_click()
    {
        if (this.autoUpdate == true)
        {
            this.myTree.stop_periodicTreeUpdate();
            this.autoUpdate = false;
            $('#'+this.instanceName+"updatetreebtn").html('<i class="fas fa-sync-alt"></i>');
        }
        else
        {
            this.autoUpdate = true;
            this.myTree.start_periodic_tree_update();
            $('#'+this.instanceName+"updatetreebtn").html('<i class="fas fa-sync-alt fa-spin"></i>');
        }

    }

}