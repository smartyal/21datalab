function http_get(myUrl) {
    
	var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", myUrl, false ); // syncronous request
    xmlHttp.send( null );
    return xmlHttp.responseText;
}


function http_post(url, data, cb)
{
    // construct an HTTP request
    var xhr = new XMLHttpRequest();
    xhr.open("POST", url, true); //asynchronous call
    xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            if (xhr.status == 200) {
                cb(xhr.responseText);
            }
            else
            {
                console.log("error calling ",url,xhr.status)
            }
        }
    }
    // send the collected data as JSON
    xhr.send(data);
}