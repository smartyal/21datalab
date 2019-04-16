var templates = null; // global list with available templates
var periodicTreeUpdate = false; //
var globalCopyBuffer = [];

var globalIconType = "standard"; // use to ingest html styles for the icons


function start_periodic_tree_update()
{
    periodicTreeUpdate = true;
    window.setTimeout(trigger_tree_update,1000)
}

function stop_periodicTreeUpdate()
{
    periodicTreeUpdate = false;
}

function trigger_tree_update()
{
    if (periodicTreeUpdate == true)
    {
        tree_update();
        window.setTimeout(trigger_tree_update,1000);
    }
}


function tree_initialize() {
    $('#jstree_div').jstree();
    tree_generate();

    //get the templates
    data = http_get('/templates')
    try
    {
        templates = JSON.parse(data);
    }
    catch(err)
    {
        return;
    }
    //start_periodic_tree_update();

    $('#jstree_div').on("select_cell.jstree-grid",function (e,data) {
        //alert( "The user double clicked a jstreegrid cell"+data.column+"  "+data.value+ );
        var id = data.node.get()[0].id;
        var value = treeNodes[id].value;
        //we only edit variables, consts
        if ( (treeNodes[id].type == "variable") || (treeNodes[id].type == "const") )
        {
            //only vars and consts can be edited
            $('#editNodeModalName').text(treeNodes[id].browsePath);
            $('#editNodeModalValue').val(JSON.stringify(treeNodes[id].value));
            $('#editNodeModalId').val(id);
            $('#editNodeModal').modal('show');
        }
    });



    $('#editNodeModalButtonSave').click(function(){
        var id = $('#editNodeModalId').val();
        var value = JSON.parse($('#editNodeModalValue').val());
        var query=[{"id":id,"value":value}];
        http_post("/setProperties",JSON.stringify(query),null,null);
    });





}

//https://fontawesome.com/icons
var treeIconsOld =
{
    root : "fa fa-folder fa-sm",
    root : "far fa-folder",
    //folder : "fa fa-folder fa-sm",
    folder : "far fa-folder",
    variable:"fas fa-random",
    timeseries : "fas fa-chart-line fa-xs",
    table :"fas fa-table",
    annotation: "fas fa-pencil-alt",
    widget : "fas fa-chart-line fa-xs",
    column :"fas fa-columns",
    const :  "fas fa-sliders-h",
    referencee : "fas fa-link",
    function : "fa fa-play-circle",
    referencer : "fas fa-share",
    reference : "fa fa-link",
    template : "fa fa-file-text-o",
    add : "fas fa-plus",
    delete : "far fa-trash-alt",
    rename : "fas fa-pencil-alt",
    changevalue : "fas fa-edit",
    execute : "fa fa-play",
    abort : "fa fa-stop",
    file:"far fa-file-alt",
    copy:"far fa-copy",
    paste: "fas fa-paint-roller"
};

var treeIconsPath = 'modules/font-awesome/svgs/regular/'
var treeIcons =
{
    root : "folder.svg",
    folder : "folder.svg",
    variable : "sticky-note.svg",
    timeseries : "chart-bar.svg",
    const : "dot-circle.svg",
    function : "play-circle.svg",
    referencer : "share-square.svg",

};

'modules/font-awesome/svgs/regular/folder.svg'

var treeTypes=
{
    "default" : {
        "icon": "fa fa-play"
    },
    "root":{
        "icon": treeIcons.root
    },
    "folder" : {
        "icon": treeIcons.folder
    },
    "const": {
        "icon":  treeIcons.const
    },
    "function": {
        "icon": treeIcons.function
    },
    "variable": {
        "icon": treeIcons.variable
    },
    "referencer": {
        "icon": treeIcons.referencer
    },
    "reference": {
        "icon" :  treeIcons.reference
    },
    "timeseries":{
        "icon":"fa fa-play"
    }
}

var diffHandle = null;
var treeNodes = null; //holding the current treeNodes

function tree_generate()
{
    $('#jstree_div').jstree("destroy");
    //data = http_get("/_getall");
    var data = http_get("_diffUpdate"); //the diff update call without data return a handle and the full model

    try
    {
        var parsed = JSON.parse(data);
        var model = parsed.model;
        diffHandle = parsed.handle; //this is a global
    }
    catch(err)
    {
        return;
    }


    var nodes = create_children(model,'1');
    treeNodes = model; //keep a copy in the global

    var myTree = {
        'plugins':["grid","contextmenu","types"],
        'core': {
            "themes" : {
                "variant" : "small"
            },
            'data': [
                 {
                    'text': ' root',
                    'state': {
                        "opened": true,
                        "selected": false
                    },
                    'id': '1',
                    'modelId': '1',
                    'type': globalIconType,
                    'icon':treeIconsOld["root"],
                    'children': nodes,
                    data: {}
                }
            ],
            'check_callback' : function(operation, node, node_parent, node_position, more) {
                console.log('check_callback' + operation + " " + node.id + " " + node_parent.text);
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
            items:function(node){
                var menuObject={
                    "delete": {
                        "label": "delete",
                        "action": function (obj) {context_menu_delete(node);},
                        "icon": treeIconsOld["delete"]
                    }
                };

                //creation is only for non-referencer
                if ((node.id in treeNodes) && (treeNodes[node.id].type != "referencer"))
                {
                    menuObject["create"]={
                        "label":"new",
                        "icon":treeIconsOld["add"],
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
                                        "action":function(obj){context_menu_create(node,"folder");},
                                        "icon":treeIconsOld["folder"]
                                    },
                                    "variable":
                                    {
                                        "label":"variable",
                                        "action":function(obj){context_menu_create(node,"variable");},
                                        "icon":treeIconsOld["variable"]
                                    },
                                    "const":
                                    {
                                        "label":"const",
                                        "action":function(obj){context_menu_create(node,"const");},
                                        "icon":treeIconsOld["const"]
                                    },
                                    "file":
                                    {
                                        "label":"file",
                                        "action":function(obj){context_menu_create(node,"file");},
                                        "icon":treeIconsOld["file"]
                                    },
                                    "referencer":
                                    {
                                        "label":"referencer",
                                        "action":function(obj){context_menu_create(node,"referencer");},
                                        "icon":treeIconsOld["referencer"]
                                    },
                                    "column":
                                    {
                                        "label":"column",
                                        "action":function(obj){context_menu_create(node,"column");},
                                        "icon":treeIconsOld["column"]
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
                    for (var template of templates)
                    {
                        //var template = templ
                        var entry = {
                            "label":template,
                            "__templateType":template, //to store it here, so we get it back on the call
                            "action":function(obj){context_menu_create_template(node,obj.item.__templateType);}
                        }
                        menuObject.create.submenu.template.submenu[template]=entry;

                    }
                }

                //if this node is a function, execution is also possible
                if ((node.id in treeNodes) && (treeNodes[node.id].type == "function"))
                {

                    menuObject["execute"] = {
                        "label": "execute",
                        "action": function(obj){context_menu_execute(node);},
                        "icon": treeIconsOld["function"]
                    }
                }

                //if this node is not a referencee node, renaming is possible
                if ((node.original.nodeType != "referencee"))
                {

                    menuObject["rename"] = {
                        "label": "rename",
                        "action": function(obj){context_menu_rename(node);},
                        "icon": treeIconsOld["rename"]
                    }
                }

                // for variables and const also editing is possible
                if ((node.original.nodeType == "variable") || (node.original.nodeType == "const"))
                {
                    menuObject["editvalue"] ={
                        "label" : "edit value",
                        "action" : function(obj){context_menu_change_value(node);},
                        "icon": treeIconsOld["changevalue"]
                    }
                }


                //if all selected nodes are not referencees, then copy is possible
                var allNodes = $('#jstree_div').jstree(true).get_selected();
                var isReferencee=false;
                for (nodeId of allNodes)
                {
                    var node = $('#jstree_div').jstree(true).get_node(nodeId);
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
                        "action": function(obj){context_menu_copy(node);},
                        "icon": treeIconsOld["copy"]
                    }
                }

                //for referencees, paste is possible
                if (node.original.nodeType == "referencer")
                {
                    menuObject["paste"] = {
                        "label": "paste",
                        "action": function(obj){context_menu_paste(node);},
                        "icon": treeIconsOld["paste"]
                    }
                }


                return menuObject;
            }
        },
        'types':{
            "standard":{"a_attr":{"style":"color:#606060;background-color:white"}},
            "inverse":{"a_attr":{"style":"color:white;background-color:grey"}},
        }
    }

    $('#jstree_div').jstree(myTree);
}


function context_menu_delete(node)
{
    console.log("context delete",node);
    //deleting is different for referencee nodes, these are in fact references
    var allNodes = $('#jstree_div').jstree(true).get_selected();
    http_post("/_delete",JSON.stringify(allNodes),null,null);

    //now for the referencees here, we remove the refs
    var allRefs={}; //all refs holds the parent:[list of references o delete]
    var allNormalNodes = []; //list of al normal nodes to delete

    for (nodeId of allNodes)
    {
        var node = $('#jstree_div').jstree(true).get_node(nodeId);
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
        http_post("/_delete",JSON.stringify(allNormalNodes),null,null);
    }

    //we must delete some references
    if (Object.keys(allRefs).length !=0)
    {
        for (var parent in allRefs)
        {
            var query={"parent":parent,"remove":allRefs[parent]};
            http_post("/_references",JSON.stringify(query),null,null);
        }
    }
}

function context_menu_execute(node)
{
    console.log("context execute",node);
    var query=node.id;
    http_post("/_execute",JSON.stringify(query),null,null);
}

function context_menu_create_template(node,templateType)
{
    console.log("create template",node,templateType);
    var splitted = templateType.split('.');
    var templateName = splitted.pop();
    var newBrowsePath = treeNodes[parseInt(node.id)].browsePath+".new_"+templateName+"_"+Math.random().toString(16).substring(2,6);
    var query={"type":templateType,"browsePath":newBrowsePath};
    http_post('/_createTemplate',JSON.stringify(query),null);
}

function context_menu_rename(node)
{
    $('#jstree_div').jstree(true).edit(node,null,edit_node_done);
}

function context_menu_create(node,type)
{
    var newBrowsePath = treeNodes[parseInt(node.id)].browsePath+".new_"+type+"_"+Math.random().toString(16).substring(2,6);
    var query=[{"browsePath":newBrowsePath,"type":type}];
    console.log("create ",newBrowsePath);
    http_post('/_create',JSON.stringify(query),node,null);
}

function context_menu_copy(node)
{

    var allNodes = $('#jstree_div').jstree(true).get_selected();
    globalCopyBuffer = allNodes;
    console.log("context_menu_copy ",allNodes);

}

function context_menu_paste(node)
{
    console.log("paste",node,globalCopyBuffer);
    //if type(globalCopyBuffer)
    var query={"parent":node.id,"add":globalCopyBuffer};
    http_post("/_references",JSON.stringify(query),null,null);
}


function context_menu_change_value(node)
{
        var id = node.id;
        var value = treeNodes[id].value;
        //only vars and consts can be edited
        $('#editNodeModalName').text(treeNodes[id].browsePath);
        $('#editNodeModalValue').val(JSON.stringify(treeNodes[id].value));
        $('#editNodeModalId').val(id);
        $('#editNodeModal').modal('show');
}



function edit_node_done(node, status, cancel)
{
    // we check if the new name is allowed: it must be unique under the parent
    console.log("edit node done",status,cancel);

    var children = treeNodes[parseInt(node.parent)].children;
    var originalName = treeNodes[parseInt(node.id)].name;
    var newName = node.text;

    if ((newName == originalName)  ||  (cancel == true))
    {
        //still the old name, nothing to do
        console.log("old name,nothing to do, cancel ");
        return ;
    }

     //iterate over the children
    for (var child in children)
    {
        var brotherName = treeNodes[parseInt(children[child])].name;
        if (brotherName == newName)
        {
            //not allowed , bring back the old name
            $('#jstree_div').jstree(true).rename_node(node,originalName);
            console.log("not allowed name exist under parent");
            return;
        }
    }
    var query=[{id:node.id,name:newName}];
    var params={id:node.id,'originalName':originalName,'newName':newName};
    http_post('/setProperties',JSON.stringify(query), params, function(status,data,params)   {
        if (status!=200)
        {
            //backend responded bad, we must set the frontend back
            $('#jstree_div').jstree(true).rename_node(node,params.originalName);
            console.log("renameing did not work on backend");
        }
        else
        {
            //all good, we also adjust the settings in our local view
            treeNodes[params.id].name=params.newName;
            treeNodes[params.id].browsePath = (treeNodes[params.id].browsePath.split('.').slice(0,-1)).join('.')+'.'+params.newName;
        }
    });


    console.log("change to new name!", newName);
}




//get the differential tree
function tree_update()
{

   var query = {handle: diffHandle};
   http_post('/_diffUpdate/', JSON.stringify(query),null,tree_update_cb);
}

function tree_update_cb(status,data,params)
{
    if (status > 201) return;

    try
    {
        var updateData =JSON.parse(data);
        diffHandle = updateData.handle; //remember this for the next time
    }
    catch
    {
        return;
    }

    //remove deleted nodes from the tree
    for (var i=0;i<updateData.deletedNodeIds.length;i++)
    {
        var deleteId = updateData.deletedNodeIds[i];
        delete treeNodes[parseInt(deleteId)]; //remove it from the global tree
        var res = $('#jstree_div').jstree().delete_node(deleteId);
        console.log("deleting id ",deleteId,res);
        // missing here is the synchronization with the treeNodes: the parent still holds the id in it's list,
        // this will be fixed when we look for the modifications:
        // the parent will be in the modified nodes list, finally we will take over the new node dict of the parent
    }

    //add new nodes
    for (var newNodeId in updateData.newNodes)
    {
        var node = updateData.newNodes[newNodeId];
        console.log("new node",node.id)
        var treeNode = node_to_tree(node);
        $("#jstree_div").jstree(true).create_node(node.parent, treeNode);
        treeNodes[newNodeId] = node; //store the nodedict info in the tree
        // missing here is the synchronization with the treeNodes: the parent still holds the id in it's list,
        // this will be fixed when we look for the modifications:
        // the parent will be in the modified nodes list, finally we will take over the new node dict of the parent
    }

    //synchronize modified nodes
    for (var id in updateData.modifiedNodes)
    {
        var newNode = updateData.modifiedNodes[id];
        var oldNode = treeNodes[parseInt(id)];

        // we will take over the full property dictionary, but we also must do some special things
        // for properties that have an importance for the front end; these are:
        // name, value, children and references
        // check if any property relevant for thehas changed

        //check name changes
        if (newNode.name != oldNode.name)
        {
            $('#jstree_div').jstree(true).rename_node(id, newNode.name);
        }

        //check value changes
        if (newNode.value != oldNode.value)
        {
            var tree = $('#jstree_div').jstree(true);
            var treeNode = tree.get_node(id);
            //trigger the redraw of the node, unfortunately all other redraw(), refresh() etc. do not trigger the grid refresh
            treeNode.data.value = JSON.stringify(newNode.value);
            treeNode["a_attr"]={"title":JSON.stringify(newNode.value),"class":"show_tooltip"};
            tree.rename_node(id,newNode.name); // same name as it was, this is to trigger the redraw
        }

        //check modification of dependencies: children and references
        if (newNode.children.toString() != oldNode.children.toString())
        {
            //iterate over the array

            for (index =0; index < newNode.children.length;index++)
            {
                if (newNode.children[index] != oldNode.children[index])
                {
                    var result = $('#jstree_div').jstree(true).move_node(newNode.children[index],newNode.id,index);
                    console.log("move ",newNode.children[index]," to parent ",newNode.id,"on position ", index,"jstreeresult:",result);
                }
            }
            //children have changed
        }

        if (newNode.forwardRefs.toString() != oldNode.forwardRefs.toString())
        {
            //references have changed, we take the brute force by rebuilding all refs from scratch
            // for this, we iterate over the children of the referencer - js tree node
            // we must use the real node of the jstree, as the reference - node are
            // only create on the js tree, not in the models
            var children = $('#jstree_div').jstree(true).get_node(oldNode.id).children;
            var result = $('#jstree_div').jstree(true).delete_node(children);
            console.log("deleted reference nodes ",children.toString()," from ",oldNode.id,"result ",result);

            //now rebuild them
            for (entry in newNode.forwardRefs)
            {
                var targetId = newNode.forwardRefs[entry];
                var referenceeModelNode = {
                        'type': 'referencee',
                        'name': treeNodes[targetId].browsePath,
                        'parent': newNode.id,
                        'targetId' : targetId //for later
                };
                var referenceeNode = node_to_tree(referenceeModelNode);
                var result = $('#jstree_div').jstree(true).create_node(newNode.id,referenceeNode);
                console.log("built reference",referenceeModelNode.name,result);
            }
        }
        treeNodes[id] = newNode; // update the new properties including children, refs etc
    }
}


 //returns an array of children ready for the tree
function create_children(model,parentNodeId)
{
    var childNodes =[];
    var childrenIds = model[parentNodeId].children;
    if (childrenIds.length>0)
    {
        for (index in childrenIds)
        {
            var childNodeId = childrenIds[index];
            var childNode = model[childNodeId];
            var treeNode = node_to_tree(childNode);
            //some more stuff
            treeNode.data.nodeid=childNodeId;
            //treeNode.data['value']=childNode['value'];

            if (childNode.children.length>0)
            {
                //this childnode has children itself, make them
                treeNode.children = create_children(model,childNodeId);
            }
            else
            {
                //no more children, but maybe this is a referecer?
                treeNode.children=[];
                if (childNode.type =="referencer")
                {

                    for (entry in childNode.forwardRefs)
                    {
                        var targetId = childNode.forwardRefs[entry];
                        var referenceeModelNode = {

                                'type': 'referencee',
                                'name': model[targetId].browsePath,
                                'parent': childNode.id,
                                'targetId' : targetId
                        };
                        var referenceeNode = node_to_tree(referenceeModelNode);
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


function node_to_tree(modelNode)
{
    //parse the model Node, we expect the parent to be there already
    var newTreeNode = {
            /*
            "a_attr": { //or a_attr if you prefer
                "title": "my tooltip text",
                "class": "show_tooltip"
            },
            */
            'id': modelNode.id,
            'parent': modelNode.parent,
            'type': globalIconType,
            'nodeType':modelNode.type,
            'text': modelNode.name,
            'state': {
                'opened': false,
                'selected': false
            },
            'children': [],
            'data': {},
            'icon': treeIconsOld[modelNode.type]//'fa fa-folder-o'//"fa fa-play o",//"fa fa-folder-o",//treeIconsPath+treeIcons[modelNode.type]
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

