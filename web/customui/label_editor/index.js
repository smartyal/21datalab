/* move this to cockpit widget later */
var cockpitPath = ""
var initialLabels = []
var currentLabels = []

var masterFrontend = null
var slaveFrontends = []

function LabelColor(hexCode, pattern) {
  o = new Object();
  o.hexCode = hexCode;
  o.pattern = pattern;
  return o;
}

function Label(name, color) {
  o = new Object();
  o.name = name
  o.color = color;
  return o;
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
    let label = Label(labelName, LabelColor(colorDict["color"], colorDict["pattern"]));
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
  http_post('_getleaves', cockpitPath + '.annotations', null, null, function(obj,status,data,params) {
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

// taken from https://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
// Version 4.0
function pSBC(p,c0,c1,l) {
    let r,g,b,P,f,t,h,i=parseInt,m=Math.round,a=typeof(c1)=="string";
    if(typeof(p)!="number"||p<-1||p>1||typeof(c0)!="string"||(c0[0]!='r'&&c0[0]!='#')||(c1&&!a))return null;
    if(!this.pSBCr)this.pSBCr=(d)=>{
        let n=d.length,x={};
        if(n>9){
            [r,g,b,a]=d=d.split(","),n=d.length;
            if(n<3||n>4)return null;
            x.r=i(r[3]=="a"?r.slice(5):r.slice(4)),x.g=i(g),x.b=i(b),x.a=a?parseFloat(a):-1
        }else{
            if(n==8||n==6||n<4)return null;
            if(n<6)d="#"+d[1]+d[1]+d[2]+d[2]+d[3]+d[3]+(n>4?d[4]+d[4]:"");
            d=i(d.slice(1),16);
            if(n==9||n==5)x.r=d>>24&255,x.g=d>>16&255,x.b=d>>8&255,x.a=m((d&255)/0.255)/1000;
            else x.r=d>>16,x.g=d>>8&255,x.b=d&255,x.a=-1
        }return x};
    h=c0.length>9,h=a?c1.length>9?true:c1=="c"?!h:false:h,f=this.pSBCr(c0),P=p<0,t=c1&&c1!="c"?this.pSBCr(c1):P?{r:0,g:0,b:0,a:-1}:{r:255,g:255,b:255,a:-1},p=P?p*-1:p,P=1-p;
    if(!f||!t)return null;
    if(l)r=m(P*f.r+p*t.r),g=m(P*f.g+p*t.g),b=m(P*f.b+p*t.b);
    else r=m((P*f.r**2+p*t.r**2)**0.5),g=m((P*f.g**2+p*t.g**2)**0.5),b=m((P*f.b**2+p*t.b**2)**0.5);
    a=f.a,t=t.a,f=a>=0||t>=0,a=f?a<0?t:t<0?a:a*P+t*p:0;
    if(h)return"rgb"+(f?"a(":"(")+r+","+g+","+b+(f?","+m(a*1000)/1000:"")+")";
    else return"#"+(4294967296+r*16777216+g*65536+b*256+(f?m(a*255):0)).toString(16).slice(1,f?undefined:-2)
}

function createHoverMap(labels) {
  // simply sort alphabetically
  let labelsSorted = [...labels].filter(label => label != null).sort((left, right) => left.name.localeCompare(right.name));
  let labelNames = labelsSorted.map(label => label.name);
  console.log("labelsSorted=", labelNames);
  let labelIndexToColorMap = Object.fromEntries(
    Object.entries(labelsSorted).map(
      ([index, label]) => [index.toString(), pSBC(-0.4, label.color.hexCode)]
    )
  );
  // for logistic_regression.categoryMap
  let labelNameToIndexMap = Object.fromEntries(
    Object.entries(labelNames).map(
      ([index, labelName]) => [labelName, index]
    )
  );
  return [labelNameToIndexMap, labelIndexToColorMap];
}

function saveLabels(labels) {
  let labelsDict = convertLabelsToDict(labels);
  // set everything to visible by default
  // TODO: store visibility information in label class to preserve it
  // ignore deleted labels marked with null
  let visibleTagsDict = Object.fromEntries(labels.filter(label => label != null).map(label => [label.name, true]));
  [labelNameToIndexMap, labelIndexToColorMap] = createHoverMap(labels);

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
    http_post(
      '/setProperties',
      JSON.stringify([ { browsePath: slaveFrontend + '.backgroundMap', value: labelIndexToColorMap } ]),
      null, null, null
    )
  }
  // TODO: remove me this is non-generic
  http_post(
    '/setProperties',
    JSON.stringify([ { browsePath: 'root.logistic_regression.categoryMap', value: labelNameToIndexMap } ]),
    null, null, null
  )
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
  let labelNames = currentLabels.filter(label => label != null).map(label => label.name);
  let i = 0;
  while (true) {
    if (labelNames.includes(labelName)) {
      labelName = "NewLabel" + i;
      ++i;
    } else {
      break;
    }
  }
  currentLabels.push(Label(labelName, new LabelColor("#000000", null)));
  updateLabelsView(currentLabels);
}

function removeLabel(labelId) {
  let labelName = currentLabels[labelId].name;
  console.log("Trying to remove label labelID=", labelId, ", labelName=", labelName);
  currentLabels[labelId] = null;
  updateLabelsView(currentLabels);
}


function cockpit_close() {
  console.log("currentLabels=", currentLabels);
  console.log("initialLabels=", initialLabels);
  updateBackend(currentLabels, initialLabels);
}
