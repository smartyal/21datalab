function http_get(myUrl) {
    
	var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", myUrl, false ); // syncronous request
    xmlHttp.send( null );
    return xmlHttp.responseText;
}


function http_post(url, data, params, obj,cb)
{
    // construct an HTTP request
    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true); //asynchronous call
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE)
        {
            if (xhr.status > 201)
            {
                console.log("error calling ",url,xhr.status);
            }
            if (cb != null)
            {
                cb(obj,xhr.status,xhr.responseText,params);
            }
        }
    }
    // send the collected data as JSON
    xhr.send(data);
}


function http_post_sync( url, jsonStringify, data ) {
  let xhr = new XMLHttpRequest()
  let inputData
  if ( jsonStringify === true ) {
    inputData = JSON.stringify(data)
  } else {
    inputData = data
  }
  xhr.open("POST", url, false)
  xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8')
  xhr.send(inputData)
  return xhr
}