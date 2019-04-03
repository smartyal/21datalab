function tree_initialize() {
    $('#jstree_div').jstree();
    tree_generate();
}

//https://fontawesome.com/icons
var treeIconsOld =
{
    root : "fa fa-folder fa-sm",
    folder : "far fa-folder",
    variable : "far fa-square",
    timeseries : "fas fa-chart-line fa-xs",
    table :"fas fa-table",
    annotation: "fas fa-pencil-alt",
    widget : "fas fa-chart-line fa-xs",
    column :"fas fa-columns",
    const : "far fa-dot-circle",//"fas fa-equals",
    referencee : "fas fa-ghost",
    function : "fa fa-play-circle",
    referencer : "fas fa-share",
    reference : "fa fa-link",
    template : "fa fa-file-text-o",
    add : "fa fa-plus",
    delete : "fa fa-remove",
    rename : "fa fa-pencil-square-o",
    execute : "fa fa-play",
    abort : "fa fa-stop"
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
        'plugins':["grid"],
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
                    'type': "root",
                    'icon':"fa fa-folder",//treeIconsPath+treeIcons["root"],
                    'children': nodes,
                    data: {}
                }
            ],
            'check_callback' : function(operation, node, node_parent, node_position, more) {
                console.log('check_callback' + operation + " " + node.id + " " + node_parent.text);
                return true; //we allow all operations as default
            }

        },
        grid: {
            columns: [
                { header: "Nodes" },
                { header: "Value", value:"value"}
                //{ header: "Value", value:"value"}function(node){return(node.data.value);
            ]
        }
        //'types':treeTypes,
        //"themes" : {"variant" : "small"}
    }
    $('#jstree_div').jstree(myTree);

}


//get the differential tree
function tree_update()
{

   var query = {handle: diffHandle};
   http_post('/_diffUpdate/', JSON.stringify(query),tree_update_cb);
}

function tree_update_cb(data)
{
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
    }

    //add new nodes
    for (var newNodeId in updateData.newNodes)
    {
        var node = updateData.newNodes[newNodeId];
        console.log("new node",node.id)
        var treeNode = node_to_tree(node);
        $("#jstree_div").jstree(true).create_node(node.parent, treeNode);
        treeNodes[newNodeId] = node; //store the info in the tree
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

        if (newNode.name != oldNode.name)
        {
            $('#jstree_div').jstree(true).rename_node(id, newNode.name);
        }

        if (newNode.value != oldNode.value)
        {
            var tree = $('#jstree_div').jstree(true);
            var treeNode = tree.get_node(id);
            //trigger the redraw of the node, unfortunately all other redraw(), refresh() etc. do not trigger the grid refresh
            treeNode.data.value = newNode.value;
            tree.rename_node(id,newNode.name); // same name as it was
        }

        treeNodes[id] = newNode; // update the new properties
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
            treeNode.data['value']=childNode['value'];

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
                                'parent': childNode.id
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
            'id': modelNode.id,
            'parent': modelNode.parent,
            'type': modelNode.type,
            'text': modelNode.name,
            'state': {
                'opened': false,
                'selected': false
            },
            'children': [],
            'data': {},
            'icon': treeIconsOld[modelNode.type]//'fa fa-folder-o'//"fa fa-play o",//"fa fa-folder-o",//treeIconsPath+treeIcons[modelNode.type]
    };

    if ((newTreeNode.type == "const")  || (newTreeNode.type == "variable"))
    {
        newTreeNode.data.value = modelNode.value;
    }
    return newTreeNode;
}

