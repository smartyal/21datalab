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

function tree_generate()
{
    $('#jstree_div').jstree("destroy");
    data = http_get("/_getall");

    try
    {
        var model = JSON.parse(data);
    }
    catch(err)
    {
        return;
    }


    var nodes = create_children(model,'1');

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
            ]
        },
        grid: {
            columns: [
                { header: "Nodes" },
                { header: "Value", value:"value"}
            ]
        }
        //'types':treeTypes,
        //"themes" : {"variant" : "small"}
    }
    $('#jstree_div').jstree(myTree);

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
            'text': ' '+modelNode.name,
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

