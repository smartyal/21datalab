
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


function on_first_load () {
	
	//register menue calls#
	$('.selectpicker').selectpicker();
	$('#reloadtreebtn').click( function () {
		tree_initialize();
	});

	$('#updatetreebtn').click( function () {
		tree_update();
	});

	$('#loadModelbtn').click( function () {
	    var name = $('#modelNameInput').val();
		load_tree(name);
	});

	$('#saveModelbtn').click( function () {
	    var name = $('#modelNameInput').val();
		save_tree(name);
	});



    $('#pipelinebutton').on('click',function () {
        target = $('#pipelineselect option:selected').text();
		var win = window.open(pipelines[target], '_blank');
        win.focus();
	});
	//tree_initialize();



	//populate piplelines menue
	var data = http_get("/pipelines");
	populate_dropdown(data);


	//load the bokeh widget for the data scientist to the embed, standard on 5006
	http_post("http://localhost:6001/embedbokeh",JSON.stringify({"url":"http://localhost:5006/bokeh_web"}),null, function(status,data,params)   {
        if (status==200)
        {
            $('#embed').html(data);
        }
    });

	//load the bokeh widget for the self-service to the self-service, for now on 5007
	http_post("http://localhost:6001/embedbokeh",JSON.stringify({"url":"http://localhost:5007/bokeh_web"}),null, function(status,data,params)   {
        if (status==200)
        {
            $('#self-service-embed').html(data);
        }
    });




}

$( document ).ready(function() {
    console.log( "ready!" );
    on_first_load();
});



