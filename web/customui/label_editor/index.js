/* move this to cockpit widget later */
var cockpitPath = ""
var initialLabels = []
var currentLabels = []

var masterFrontend = null
var slaveFrontends = []

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
    if (label == null)
      continue;
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
  // reset state variables
  initialLabels = []
  currentLabels = []
  http_post("_getbranchpretty", JSON.stringify({'node':  cockpitPath + '.master_frontend', 'depth': 1}), null, null, function(obj,status,data,params) {
    if (status == 200) {
      let res = JSON.parse(data)[".properties"]["targets"];
      if (res.length == 0) {
        console.log("Referencer master_frontend does not contain any reference to a frontend. Exiting!")
        return;
      }
      masterFrontend = res[0];

      console.log("label_editor.cockpit_init: masterFrontend", masterFrontend);
      // colors contains a dictionary mapping from
      http_post("_getvalue",JSON.stringify([masterFrontend + '.hasAnnotation.colors']), null, null, function(obj,status,data,params) {
        if (status == 200) {
          labelNameColorDict = JSON.parse(data)[0];
          currentLabels = convertDictToLabels(labelNameColorDict);
          initialLabels = convertDictToLabels(labelNameColorDict);
          updateLabelsView(currentLabels);
        }
      });
    }
  });
  http_post("_getbranchpretty", JSON.stringify({'node':  cockpitPath + '.slave_frontends', 'depth': 1}), null, null, function(obj,status,data,params) {
    if (status == 200) {
      let res = JSON.parse(data)[".properties"]["targets"];
      slaveFrontends = res;
      console.log("label_editor.cockpit_init: slaveFrontends", slaveFrontends);
    }
  });
}

function updateLabelColor(labelId, labelColorString) {
  currentLabels[labelId].color.hexCode = labelColorString;
}

function updateLabelsView(labels) {
    const selector = '#label-table-body'
    let tableRowHtml = '';
    let removeButtonHtml = '';
    for (const [labelId, label] of labels.entries()) {
        // label has been deleted
        if (label == null)
            continue;
        let labelNameInputId = "labelName" + labelId;
        removeButtonHtml = '<button type="button" class="btn btn-primary" onclick="removeLabel(' + labelId + ')">Remove</button>';
        tableRowHtml += '<tr><td><input type="text" minlength="1" value="' + label.name + '" id="' + labelNameInputId + '">'
            + '<button type="button" class="btn btn-primary" onclick="changeLabelName(' + labelId + ', document.querySelector(\'#' + labelNameInputId + '\').value)">Save</button></td>'
            + '<td><input type="color" value="' + label.color.hexCode + '" onchange="updateLabelColor(\'' + labelId + '\', this.value)"></td>'
            + '<td>' + removeButtonHtml + '</td></tr>'
    }
    $(selector).html(tableRowHtml)
}

function getExistingAnnotationNodes(labelNames, callable) {
  http_post('_getleaves', masterFrontend + '.hasAnnotation.annotations', null, null, function(obj,status,data,params) {
    if (status == 200) {
      let nodes = JSON.parse(data);
      let annotationNodes = []
      for (const node of nodes) {
        let typeNode = node['children'].filter(n => n['name'] == 'type')[0];
        let tagsNode = node['children'].filter(n => n['name'] == 'tags')[0];
        let type = typeNode['value'];
        let tags = tagsNode['value'];
        if (type == 'time' && labelNames.includes(tags[0])) {
          annotationNodes.push(node);
        }
      }
      callable(annotationNodes);
    }
  });
}

function changeLabelName(labelId, newName) {
  currentLabels[labelId].name = newName;
}

function renameExistingAnnotations(oldNameToNewNameDict) {
  getExistingAnnotationNodes(Object.keys(oldNameToNewNameDict), annotationNodes => {
    console.log('Need to update ' + annotationNodes.length + ' existing annotations with labels', Object.keys(oldNameToNewNameDict));
    for (const annotationNode of annotationNodes) {
      let tagsNode = annotationNode['children'].filter(n => n['name'] == 'tags')[0];
      let oldName = tagsNode['value'][0];
      let newName = oldNameToNewNameDict[oldName];
      console.log("Updating annotation", tagsNode['browsePath'], ':', oldName, '->', newName);
      // need to update
      http_post(
        '/setProperties',
        JSON.stringify([ { 'id': tagsNode['id'], 'value': [newName] } ]),
        null, null, null
      );
    }
  });
}

function deleteExistingAnnotations(labelNames) {
  getExistingAnnotationNodes(labelNames, annotationNodes => {
    for (const annotationNode of annotationNodes) {
      let tagsNode = annotationNode['children'].filter(n => n['name'] == 'tags')[0];
      let label = tagsNode['value'][0];
      let browsePath = tagsNode['browsePath'];
      browsePath = browsePath.substr(0, browsePath.lastIndexOf('.'));
      console.log('Deleting annotation', browsePath, ' of type', label);
      http_post(
        '/_delete',
        JSON.stringify([ annotationNode['id'] ]),
        null, null, null
      );
    }
  });
}

function saveLabels(labels) {
  let labelsDict = convertLabelsToDict(labels);
  // set everything to visible by default
  // TODO: store visibility information in label class to preserve it
  // ignore deleted labels marked with null
  let visibleTagsDict = Object.fromEntries(labels.filter(label => label != null).map(label => [label.name, true]));

  for (const slaveFrontend of slaveFrontends) {
    console.log("Updating ", slaveFrontend + '.hasAnnotation.visibleTags');
    //var query = [{"id":id.substr(13),"value":true}];
    //http_post("/setProperties",JSON.stringify(query),null,null,null);
    http_post(
      '/setProperties',
      JSON.stringify([ { 'browsePath': slaveFrontend + '.hasAnnotation.visibleTags', 'value': visibleTagsDict } ]),
      null, null, null
    )
    http_post(
      '/setProperties',
      JSON.stringify([ { browsePath: slaveFrontend + '.hasAnnotation.colors', value: labelsDict } ]),
      null, null, null
    )
    http_post(
      '/setProperties',
      JSON.stringify([ { browsePath: slaveFrontend + '.hasAnnotation.tags', value: Object.keys(visibleTagsDict) } ]),
      null, null, null
    )
  }
}

function updateBackend(currentLabels, initialLabels) {
  // store labels in backend
  saveLabels(currentLabels);

  // make sure that existing annotations are consistent
  let oldNameToNewNameDict = {};
  let deletedLabelNames = [];
  for (let i = 0; i < initialLabels.length; ++i) {
    if (currentLabels[i] != null) {
      // label has not been deleted
      if (currentLabels[i].name != initialLabels[i].name) {
        oldNameToNewNameDict[initialLabels[i].name] = currentLabels[i].name;
      }
    } else {
      deletedLabelNames.push(initialLabels[i].name);
    }
  }
  if (Object.keys(oldNameToNewNameDict).length > 0) {
    if (confirm('Rename existing annotations ' + JSON.stringify(oldNameToNewNameDict) + '?')) {
      console.log("Renaming existing annotations with names " + JSON.stringify(Object.keys(oldNameToNewNameDict)));
      renameExistingAnnotations(oldNameToNewNameDict);
    }
  }
  if (deletedLabelNames.length > 0) {
    if (confirm('Delete existing annotations with labels ' + JSON.stringify(deletedLabelNames) + '?')) {
      console.log('Deleting existing annotations with labels ' + JSON.stringify(deletedLabelNames));
      deleteExistingAnnotations(deletedLabelNames);
    }
  }


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
  currentLabels[labelId] = null;
  updateLabelsView(currentLabels);
}


function cockpit_close() {
  updateBackend(currentLabels, initialLabels);
}
