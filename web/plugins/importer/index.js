// --- init
// TODO what is this doing
var cockpiteventSource = 0
var cockpitPath = ""
var cockpitWidgetPath = ""
let importerFields

function cockpit_importer_test() {
  http_post( "/_execute", cockpitPath + ".importer_import", null, null, (self, status, data, params) => {
    console.log("log",status);
  })
}
// --- initializes the cockpit
function cockpit_init(path) {
  cockpitPath = path
  $("#cockpit").attr("path",path)
  cockpit_importer_add_event_listener()
  cockpit_importer_render_files()
}

function cockpit_importer_render_files() {
  const files = JSON.parse(http_get('/_upload'));
  const filesLength = files.length;
  let filesHtml = '<b>No files available!</b>';
  if (filesLength > 0) {
    filesHtml = `<thead><tr><th>File</th><th>Action</th></tr></thead><tbody>`;
    for (var fileNo = 0, length = filesLength; fileNo < length; fileNo++) {
      const file = files[fileNo];
      filesHtml = `${filesHtml}<tr><td>${file.name}</td>
        <td><button type="button" class="btn btn-primary" onclick="cockpit_importer_file_approve('${file.name}')">import</button></td>
      </tr>`;
      console.log('file', file);
    }
    filesHtml = `<table class="table table-dark table-striped">${filesHtml}</tbody></table>`;
  }
  $("#cockpit-importer-choose-file-files").html(filesHtml);
}

// --- approve the file
function cockpit_importer_file_approve(fileName) {

  // --- adapt modal settings
  $('#tab-importer-choose-file').addClass('disabled')
  $('#tab-importer-approve-file').removeClass('disabled')
  $('#tab-importer-approve-file').click()

  // --- set filename
  let path =$("#cockpit").attr("path");
  let query = [ { browsePath: path + ".importer_preview.fileName", value: fileName} ];
  http_post( "/setProperties", JSON.stringify(query), null, null, function ( obj, status, data, params ) {

    // --- delete current data_preview
    query = [ { browsePath: path + ".importer_preview.data_preview", value: undefined } ];
    http_post( "/setProperties", JSON.stringify(query), null, null, function ( obj, status, data, params ) {

      // --- run import function
      http_post( "/_execute", cockpitPath + ".importer_preview", null, null, (self, status, data, params) => {
        console.log("log",status);
        let importerApproveHtml = ``

        if ( status !== 200 ) {

          importerApproveHtml = `<p>Something went wrong while loading the file!</p>`
          $("#cockpit-importer-approve-file").html(importerApproveHtml)

        } else {

          // --- get data from node
          http_post( "_getbranchpretty", cockpitPath + ".importer_preview.data_preview", null, null, function( obj, status, data, params ) {
            const node = JSON.parse(data)
            const value = JSON.parse(node[".properties"].value)
            importerFields = value.schema.fields
            const dat = value.data
            let fieldsHtml = `<thead>`

            // --- loop through fields
            for (var fieldNo = 1, len = importerFields.length; fieldNo < len; fieldNo++) {
              const field = importerFields[fieldNo]
              fieldsHtml = `${fieldsHtml}<th>${field.name}</th>`
            } 
            fieldsHtml = `<tr>${fieldsHtml}</tr></thead><tbody>`

            // --- loop through data
            let datHtml = ``
            for (var datNo = 0, datLen = dat.length; datNo < datLen ; datNo++) {

              const row = dat[datNo]
              console.log('row', row) 

              // --- loop through fields
              datHtml = `${datHtml}<tr>`
              for (var fieldNoDat = 1, fieldLen = importerFields.length; fieldNoDat < fieldLen; fieldNoDat++) {
                const field = importerFields[fieldNoDat]
                datHtml = `${datHtml}<td>${row[field.name]}</td>`
              } 
              datHtml = `${datHtml}</tr>`
            } 

            importerApproveHtml = `
              <div class="table-responsive">
                <table class="table table-dark table-striped">${fieldsHtml}${datHtml}</tbody></table>
              </div>
              <button type="button" class="btn btn-success" onclick="cockpit_importer_define_header(true)">File contains header</button>
              <button type="button" class="btn btn-danger" onclick="cockpit_importer_define_header(false)">File misses header</button>
            `
            $("#cockpit-importer-approve-file").html(importerApproveHtml)
          })
        }
      })
    })
  })
}

// --- define header
function cockpit_importer_define_header( fileHasHeader ) {

  // --- adapt modal settings
  $('#tab-importer-choose-file').addClass('disabled')
  $('#tab-importer-approve-file').addClass('disabled')
  $('#tab-importer-define-header').removeClass('disabled')
  $('#tab-importer-define-header').click()

  console.log('file has header:', fileHasHeader) 

  console.log('importerFields', importerFields) 
  let defineHeaderHtml = ``
  for (var fieldNo = 1, fieldsLen = importerFields.length; fieldNo < fieldsLen; fieldNo++) {
    const field = importerFields[fieldNo]
    defineHeaderHtml= `${defineHeaderHtml}
      <tr>
        <td>${field.name}</td>
        <td><input type="text"      id="importer-field-${fieldNo}-text"   value="${field.name}"></td>
        <td>
          <label class="checkbox-inline">
            <input type="checkbox"  id="importer-field-${fieldNo}-import" checked data-toggle="toggle">
          </label>
        </td>
      </tr>
    `
  }
  defineHeaderHtml = `${defineHeaderHtml}`

  defineHeaderHtml = `
    <div class="table-responsive">
      <table class="table table-dark table-striped">
        <thead>
          <tr>
            <th>Original name</th>
            <th>Adapted name</th>
            <th>Import</th>
          </tr>
        </thead>
        <tbody>
          ${defineHeaderHtml}
        </tbody>
      </table>
      <button type="button" class="btn btn-success" onclick="cockpit_importer_import()">Import</button>
    </div>
  `
  $("#cockpit-importer-define-header").html(defineHeaderHtml)

}

function cockpit_importer_import() {

  console.log('in') 

  // --- adapt modal settings
  $('#tab-importer-choose-file').addClass('disabled')
  $('#tab-importer-approve-file').addClass('disabled')
  $('#tab-importer-define-header').addClass('disabled')
  $('#tab-importer-import').removeClass('disabled')
  $('#tab-importer-import').click()


  http_post( "/_execute", cockpitPath + ".importer_import", null, null, (self, status, data, params) => {
    console.log("log",status);
  })

}

// --- closes the cockpit
function cockpit_close() {  

  // importer-choose-file
  $('#tab-importer-choose-file').removeClass('disabled')
  $('#tab-importer-choose-file').addClass('active')
  $('#importer-choose-file').addClass('active')
  $('#importer-choose-file').addClass('show')

  // importer-approve-file
  $('#tab-importer-approve-file').addClass('disabled')
  $('#tab-importer-approve-file').removeClass('active')
  $('#importer-approve-file').removeClass('active')
  $('#importer-approve-file').removeClass('show')

  // importer-import-file
  $('#tab-importer-import').addClass('disabled')
  $('#tab-importer-import').removeClass('active')
  $('#importer-import').removeClass('active')
  $('#importer-import').removeClass('show')

  $('#tab-importer-choose-file').click()
  cockpiteventSource.close();
}

// ---
function cockpit_importer_add_event_listener() {
  cockpiteventSource = new EventSource('/event/stream');
  cockpiteventSource.addEventListener('importer.data_imported', (e) => {
    console.log("importer.data_imported", e)
  });
}

// ---
function cockpit_importer_preview() {
  http_post("/_execute", cockpitPath+".importer_preview", null, null, (self, status, data, params) => {
    console.log("log",status);
  });
}

function cockpit_motif_run()
{
  //start the mining process
  let path =$("#cockpit").attr("path")+".PPSMiner";
  http_post("/_execute",JSON.stringify(path),null,null,null);
}

function cockpit_motif_stop() {
  let path =$("#cockpit").attr("path")+".PPSMiner.control.signal";
  var query = [{"browsePath":path,"value":"stop"}];
  http_post("/setProperties",JSON.stringify(query))
}
function cockpit_find_motif() {
  let start  =  $("#cockpit-select-motif-start").val();
  let end = $("#cockpit-select-motif-end").val();
  var query = [{browsePath:cockpitWidgetPath+".startTime",value:start},{browsePath:cockpitWidgetPath+".endTime",value:end}];
  http_post('/setProperties',JSON.stringify(query), null, null, null);
}
/* move this to cockpit widget later
 */
function cockpit_motif_jump_next()
{
  cockpit_motif_jump(1);
}

function cockpit_motif_jump_prev()
{
  cockpit_motif_jump(-1);
}
function cockpit_motif_jump(inc)
{
  //start the mining process
  let pathInc =$("#cockpit").attr("path")+".peakSearch.jumpInc";
  var query = [{browsePath:pathInc,value:inc}];
  http_post('/setProperties',JSON.stringify(query), null, this, (self,status,data,params) => {
    if (status>201) {
      //backend responded bad, we must set the frontend back
      console.log("context_menu_set_visible_elements",status);
    } else {
      let path =$("#cockpit").attr("path")+".peakSearch";
      http_post("/_execute",JSON.stringify(path),null,null,null);
    }
  });
}
function cockpit_set_filename() {
  var query = [{ 
    browsePath: cockpitPath+".fileName",
    value: $("#cockpit-select-motif-path").val(),
  }];
  http_post('/setProperties',JSON.stringify(query), null, this, (self,status,data,params) => {
    console.log("log",status);
  });
}


function cockpit_select_motif()
{

  var query=cockpitWidgetPath+".hasAnnotation.selectedAnnotations";
  http_post('/_getleaves',JSON.stringify(query), null, this, (self,status,data,params) => {
    if (status==200)
    {
      let motif = JSON.parse(data)[0]["browsePath"];
      $("#cockpit-select-motif-path").val(motif);
      let path =$("#cockpit").attr("path");
      var query = {"deleteExisting":true,"parent":path+".PPSMiner.motif","add":[motif]};
      http_post("/_references",JSON.stringify(query),null,null,null);
      cockpit_load_settings(); // refresh all values
    }
  });
}

function cockpit_load_settings()
{
  http_post("_getbranchpretty",cockpitPath, null,null, function(obj,status,data,params)
    {
      if (status==200)
      {
        var pipeLineData = JSON.parse(data);
        var minerData = pipeLineData.PPSMiner;

        //first the motif selection data
        var motifPath = minerData.motif[".properties"].leaves[0];
        if (motifPath)
        {
          $("#cockpit-select-motif-path").val(motifPath);

          http_post("_getbranchpretty",motifPath, null,null, function(obj,status,data,params)
            {
              if (status == 200)
              {

                var data = JSON.parse(data);
                let variable = data.variable[".properties"].leaves[0];
                let start = data.startTime[".properties"].value;
                let end = data.endTime[".properties"].value;
                $("#cockpit-select-motif-variable").val(variable);
                $("#cockpit-select-motif-start").val(start);
                $("#cockpit-select-motif-end").val(end);


              }
            });
        }

        let widgetPath = minerData.widget[".properties"].leaves[0];
        cockpitWidgetPath = widgetPath;
        http_post("_getbranchpretty",widgetPath, null,null, function(obj,status,data,params)
          {
            if (status == 200)
            {

              var data = JSON.parse(data);
              let selectedAnnotation = data.hasAnnotation.selectedAnnotations[".properties"].leaves[0];
              $("#cockpit-select-motif-current").val(selectedAnnotation);
            }
          });

        //now the settings
        $("#cockpit-parameters-algorithm").empty(); //delete the selections
        var selected = minerData.algorithm[".properties"].value;
        for (let opt of minerData.algorithm[".properties"].validation.values)
        {
          if (opt == selected)
          {
            $("#cockpit-parameters-algorithm").append("<option selected>"+JSON.stringify(opt)+"</option>");
          }
          else
          {
            $("#cockpit-parameters-algorithm").append("<option>"+JSON.stringify(opt)+"</option>");
          }
        }

        $("#cockpit-parameters-noise").val(JSON.stringify(minerData.addNoise[".properties"].value));
        $("#cockpit-parameters-subsampling").val(JSON.stringify(minerData.subSamplingFactor[".properties"].value));
        $("#cockpit-parameters-threshold").val(JSON.stringify(pipeLineData.peakSearch.threshold[".properties"].value));

        $("#cockpit-parameters-polynom").empty();
        selected = minerData.subtractPolynomOrder[".properties"].value;
        for (let opt of  minerData.subtractPolynomOrder[".properties"].validation.values)
        {
          if (opt == selected)
          {
            $("#cockpit-parameters-polynom").append("<option selected>"+JSON.stringify(opt)+"</option>");
          }
          else
          {
            $("#cockpit-parameters-polynom").append("<option>"+JSON.stringify(opt)+"</option>");
          }
        }
      }
    });
}
