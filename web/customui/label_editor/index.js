/* move this to cockpit widget later */
_helper_log('label_editor load')
var cockpitPath = ""
var currentLabels = []
var srcFrontends = []
var dstFrontends = []

class LabelColor {
  constructor(hexCode, pattern) {
    this.hexCode = hexCode;
    this.pattern = pattern;
  }
}

class Label {
  constructor(name, color) {
    this.name = name
    this.color = color;
  }
}

function convertLabelsToDict(labels) {
  dict = {}
  for (const label of labels) {
    dict[label.name] = {"color": label.color.hexCode, "pattern": null}
  }
  return dict;
}

function convertDictToLabels(labelNameColorDict) {
  //let labels = Object.entries(labelNameColorDict).map(([labelName, colorDict]) => {
  //  new Label(labelName, new LabelColor(colorDict["color"], colorDict["pattern"]));
  //});
  let labels = [];
  for (const [labelName, colorDict] of Object.entries(labelNameColorDict)) {
    let label = new Label(labelName, new LabelColor(colorDict["color"], colorDict["pattern"]));
    labels.push(label);
  }
  return labels;
}

// --- initializes the cockpit
function cockpit_init(path) {
  cockpitPath = path
  console.log('cockpitPath', cockpitPath)

  http_post("_getbranchpretty", JSON.stringify({'node':  cockpitPath + '.src_frontends', 'depth': 1}), null, null, function(obj,status,data,params) {
    if (status == 200) {
      let res = JSON.parse(data)[".properties"]["targets"];
      srcFrontends = res;

      if (srcFrontends.length == 0) {
        console.log("Referencer src_frontends does not contain any reference to a frontend. Exiting!")
        return;
      }

      console.log("label_editor.cockpit_init: srcFrontends", srcFrontends);
      // colors contains a dictionary mapping from
      http_post("_getvalue",JSON.stringify([srcFrontends[0] + '.hasAnnotation.colors']), null, null, function(obj,status,data,params) {
        if (status == 200) {
          labelNameColorDict = JSON.parse(data)[0];
          let labels = convertDictToLabels(labelNameColorDict);
          updateLabelsView(labels);
          currentLabels = labels;
        }
      });
    }
  });
  http_post("_getbranchpretty", JSON.stringify({'node':  cockpitPath + '.dst_frontends', 'depth': 1}), null, null, function(obj,status,data,params) {
    if (status == 200) {
      let res = JSON.parse(data)[".properties"]["targets"];
      dstFrontends = res;
      console.log("label_editor.cockpit_init: dstFrontends", dstFrontends);
    }
  });
}

function updateLabelColor(labelId, labelColorString) {
  console.log("updateLabelColor, labelId, labelColorstring", labelId, labelColorString);
  currentLabels[labelId].color.hexCode = labelColorString;
  //for (const label of currentLabels) {
  //  if (label.name == labelName) {
  //    label.color.hexCode = labelColorString;
  //  }
  //}
}

function updateLabelsView(labels) {
    const selector = '#label-table-body'
    let tableRowHtml = '';
    let removeButtonHtml = '';
    for (const [labelId, label] of labels.entries()) {
        let labelNameInputId = "labelName" + labelId;
        removeButtonHtml = '<button type="button" class="btn btn-primary" onclick="removeLabel(' + labelId + ')">Remove</button>';
        tableRowHtml += '<tr><td><input type="text" minlength="1" value="' + label.name + '" id="' + labelNameInputId + '">'
            + '<button type="button" class="btn btn-primary" onclick="changeLabelName(' + labelId + ', document.querySelector(\'#' + labelNameInputId + '\').value)">Save</button></td>'
            + '<td><input type="color" value="' + label.color.hexCode + '" onchange="updateLabelColor(\'' + labelId + '\', this.value)"></td>'
            + '<td>' + removeButtonHtml + '</td></tr>'
    }
    $(selector).html(tableRowHtml)
}

function changeLabelName(labelId, labelName) {
  let oldName = currentLabels[labelId].name;
  currentLabels[labelId].name = labelName;
  console.log("Updating labels from \"" + oldName + "\" to \"" + labelName + "\"");
  http_post("_getleaves", srcFrontends[0] + ".hasAnnotation.annotations", null, null, function(obj,status,data,params) {
    if (status == 200) {
      let nodes = JSON.parse(data);
      for (const node of nodes) {
        let typeNode = node["children"].filter(n => n["name"] == "type")[0];
        let tagsNode = node["children"].filter(n => n["name"] == "tags")[0];
        let type = typeNode["value"];
        let tags = tagsNode["value"];
        console.log("tags=" + JSON.stringify(tags) + ", type=" + type);
        if (type == "time" && tags[0] == oldName) {
            console.log("Updating annotation ", tagsNode["browsePath"]);
            // need to update
            http_post(
              '/setProperties',
              JSON.stringify([ { 'id': tagsNode["id"], "value": [labelName] } ]),
              null, null, null
            );
          }
        }
      }
  });

}


function updateBackend(labels) {
  let labelsDict = convertLabelsToDict(labels);
  // set everything to visible by default
  let newVisibleTagsDict = Object.fromEntries(labels.map(label => [label.name, true]));

  console.log("updateBackend - srcFrontends=", srcFrontends);
  console.log("updateBackend - labelsDict: ", JSON.stringify(labelsDict));
  console.log("updateBackend - newVisibleTagsDict: ", JSON.stringify(newVisibleTagsDict));

  let request = http_post_sync('_getvalue', true, [srcFrontends[0] + '.hasAnnotation.visibleTags']);
  //console.log("updateBackend: data=", request);
  if (request.status == 200) {
    let oldVisibleTagsDict = JSON.parse(request.response)[0];
    console.log("updateBackend - oldVisibleTagsDict: ", JSON.stringify(oldVisibleTagsDict));
    for (const [labelName, isVisible] of Object.entries(oldVisibleTagsDict)) {
      if (labelName in newVisibleTagsDict) {
        // preserve visibility information
        newVisibleTagsDict[labelName] = isVisible;
      }
    }
    console.log("updateBackend - mergedVisibleTagsDict: ", JSON.stringify(newVisibleTagsDict));
    console.log("updateBackend - dstFrontends=", dstFrontends);
    for (const dstFrontend of dstFrontends) {
      console.log("Updating ", dstFrontend + '.hasAnnotation.visibleTags');
      //var query = [{"id":id.substr(13),"value":true}];
      //http_post("/setProperties",JSON.stringify(query),null,null,null);
      http_post(
        '/setProperties',
        JSON.stringify([ { 'browsePath': dstFrontend + '.hasAnnotation.visibleTags', 'value': newVisibleTagsDict } ]),
        null, null, null
      )
      http_post(
        '/setProperties',
        JSON.stringify([ { browsePath: dstFrontend + '.hasAnnotation.colors', value: labelsDict } ]),
        null, null, null
      )
      http_post(
        '/setProperties',
        JSON.stringify([ { browsePath: dstFrontend + '.hasAnnotation.tags', value: Object.keys(newVisibleTagsDict) } ]),
        null, null, null
      )
      /*
      res = http_post_sync(
        '/setProperties',
        true,
        [ { browsePath: dstFrontend + '.hasAnnotation.visibleTags', value: newVisibleTagsDict } ]
      )
      res = http_post_sync(
        '/setProperties',
        true,
        [ { browsePath: dstFrontend + '.hasAnnotation.colors', value: labelsDict } ]
      )
      res = http_post_sync(
        '/setProperties',
        true,
        [ { browsePath: dstFrontend + '.hasAnnotation.tags', value: Object.keys(newVisibleTagsDict) } ]
      );
      */
    }
  }
}

function updateAnnotations(labels) {
  // http_post("/_delete",JSON.stringify(option.data),null,null,null);
}

function cockpit_test() {
}


function addLabel() {
  let labelName = "NewLabel";
  let labelNames = currentLabels.map(label => label.name);
  let i = 0;
  while (true) {
    if (labelNames.includes(labelName)) {
      labelName = "NewLabel" + i;
      ++i;
    } else {
      break;
    }
  }
  currentLabels.push(new Label(labelName, new LabelColor("#000000", null)));
  updateLabelsView(currentLabels);
}

function removeLabel(labelId) {
  let labelName = currentLabels[labelId].name;

  console.log("Trying to remove label labelID=", labelId, ", labelName=", labelName);
  let labels = currentLabels.filter(label => label.name != labelName);

  currentLabels = labels;
  updateLabelsView(currentLabels);
}


function cockpit_close() {
  console.log("label_editor.cockpit_close: srcFrontends=", srcFrontends);
  console.log("label_editor.cockpit_close: dstFrontends=", dstFrontends);
  updateBackend(currentLabels);
  _helper_log('cockpit_close')
}


function _helper_log(logText) {
  const length = logText.length + 4
  let header = ''
  for (var i = 0, len = length; i < len ; i++) {
    header = `${header}=` 
  } 
  console.log(header)
  console.log(`| ${logText} |`)
  console.log(header)
}
