
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
    $('#pipelinebutton').on('click',function () {
        target = $('#pipelineselect option:selected').text();
		var win = window.open(pipelines[target], '_blank');
        win.focus();
	});



	//populate piplelines menue
	var data = http_get("/pipelines");
	populate_dropdown(data);

}

$( document ).ready(function() {
    console.log( "ready!" );
    on_first_load();
});



