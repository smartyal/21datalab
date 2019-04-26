
var pipelines={};

function populate_dropdown(data)
{
    try
    {
        var pipelinesNode = JSON.parse(data);
        for (var name in pipelinesNode)
        {
            var node = pipelinesNode[name];
            var url = node.url;
            //find the url
            var entry='<option>'+name+'</option>';
            pipelines[name]=url;
            $('#pipelineselect').append(entry);
        }
    }
    catch(err)
    {
        ;
    }
}

function populate_models() {
    let data = http_get("/models");
    let models = JSON.parse(data);

    $('#modelSelect').empty();

    $('#modelSelect').append(`<option value="" disabled selected>Choose a model</option>`)

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

	//populate piplelines menue
	var data = http_get("/pipelines");
	populate_dropdown(data);


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

    //this function is triggered on dropping from the tree nodes
    $(document).on('dnd_stop.vakata', function(e, data) {
        var t = $(data.event.target);
        if(t.closest('.dropnodes').length) {
            var nodes=" ";
            for (let i = 0; i < data.data.nodes.length; i++) {
                    nodes = nodes + " " + String(data.data.nodes[i]);
            }
            let div = t.closest('.dropnodes')[0];
            let divid = div.id;
            let info = $(div).data('uicomponent');
            alert("add nodes "+nodes +"to div id"+divid+"with target"+String(info.path));
            drop_nodes(data.data.nodes,info.path);
        }

    });


}





$( document ).ready(function() {
    console.log( "ready!" );
    on_first_load();
});



