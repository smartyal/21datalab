
var nodesMoving = {}; //here we store information from the tree plugin about the move, we grab in in the dnd_stop event and execute the move



function populate_models() {
    let data = http_get("/models");
    let models = JSON.parse(data);

    $('#modelSelect').empty();

    $('#modelSelect').append('<option value="" disabled selected>Choose a model</option>')

    for (let model of models) {
        $('#modelSelect').append(`<option>` + model + `</option>`);
    }
}

function populate_settings() {
    // Try to retrieve the current setting from the local storage
    let data = localStorage.getItem("21dataSettings");

    if (data != undefined) {
        try {
            // Try to deserialize the settings into an object
            let crtSettings = JSON.parse(data);

            // Set the appropriate parameters based on the configuration
            $("#autoRefreshTree").prop('checked', crtSettings.autoRefreshTree);
            $('#themeSelect').val(crtSettings.theme);
        }
        catch {

        }
    }
}


function drop_nodes(nodeIds,path)
{
    let query={"nodes":nodeIds,"path":path};
    http_post("http://localhost:6001/dropnodes",JSON.stringify(query),null,null);
}


function on_first_load () {

	//register menue calls#
	$('.selectpicker').selectpicker();
	$('#reloadtreebtn').click( function () {
		tree_initialize();
	});

	$('#updatetreebtn').click( function () {
		tree_update();
	});

    populate_models();

	$('#loadModelBtn').click(() => {
        let modelName = $('#modelSelect').val();

        if (modelName != "") {
            load_tree(modelName);
        }
	});

	$('#saveModelBtn').click(() => {
        let modelName = $('#modelNameInput').val();

        // save_tree(modelName);
        // Trigger a model save and afterwards clear the input for the model name and update the model dropdown
        http_post('/_save', modelName, null, () => {
            $('#modelNameInput').val('');
            populate_models();
        });
	});

	//tree_initialize();

    populate_settings();

    $('#applySettings').click(() => {
        let autoRefreshTree = $('#autoRefreshTree').is(":checked");
        let theme = $('#themeSelect').val();

        // Store all the settings into the local storage
        localStorage.setItem("21dataSettings", JSON.stringify({
            "autoRefreshTree": autoRefreshTree,
            "theme": theme
        }));

        // Store the theme settings also separately, this shall be read at the beginning to set the proper theme.
        localStorage.setItem("21datalabTheme", theme);

        // Finally reload the page, which will trigger the theme change
        location.reload();
    });

	//load the bokeh widget for the data scientist to the embed, standard on 5006
	http_post("http://localhost:6001/embedbokeh",JSON.stringify({"url":"http://localhost:5006/bokeh_web"}),null, function(status,data,params)   {
        if (status==200)
        {
            $('#embed').html(data);
            $('#embed').data('uicomponent', { "engine":"bokeh","path":"root.visualization.workbench"});
        }
    });

	//load the bokeh widget for the self-service to the self-service, for now on 5007
	http_post("http://localhost:6001/embedbokeh",JSON.stringify({"url":"http://localhost:5007/bokeh_web"}),null, function(status,data,params)   {
        if (status==200)
        {
            $('#self-service-embed').html(data);
        }
    });


    tree_initialize();

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
                let info = $(div).data('uicomponent');
                console.log("drop nodes outside of the tree, model path:"+info.path);
                //alert("add nodes "+String(nodes) + "to target"+String(info.path));
                drop_nodes(data.data.nodes,info.path);
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
}





$( document ).ready(function() {
    console.log( "ready!" );
    on_first_load();
});



