/*
 * Update an object with the results of a POST request.
 *
 * An object (`$display`) is updated using the response from a POST
 * request. The request delivers a set of data (`rawData`) to the given
 * endpoint. If nothing is returned, an error is logged. Various
 * functions are defined below to peform different actions using the
 * resuls of the request.
 */

import { sendPostRequest } from 'dry-foundation/requests';


function replaceDisplayContentsRequest(
  endpoint, rawData, $display, callback = null
) {

  // The action is to replace the display's contents
  function action(response) {
    $display.html(response["content"]);
    // Execute the callback function, if given
    if (callback != null) {
      callback();
    }
  }

  // Assign the response to the display object
  sendPostRequest(endpoint, rawData, action);

}


function replaceDisplayElementRequest(
  endpoint, rawData, $display, callback = null
) {

  // The action is to replace the display element entirely
  function action(response) {
    $display.replaceWith(response["content"]);
    // Execute the callback function, if given
    if (callback != null) {
      callback();
    }
  }

  // Assign the response to the display object
  sendPostRequest(endpoint, rawData, action);

}


export { replaceDisplayContentsRequest, replaceDisplayElementRequest};
