/*
 * Update an object with the results of an AJAX request.
 *
 * An object (`$display`) is updated using the response from an AJAX
 * request. The request delivers a set of data (`rawData`) to the given
 * endpoint. If nothing is returned, an error is logged. Various
 * functions are defined below to peform different actions using the
 * resuls of the request.
 */

import { executeAjaxRequest } from './ajax.js';


function replaceDisplayContentsAjaxRequest(
  endpoint, rawData, $display, callback = null
) {

  // The action is to replace the display's contents
  function action(response) {
    $display.html(response);
    // Execute the callback function, if given
    if (callback != null) {
      callback();
    }
  }

  // Assign the response to the display object
  executeAjaxRequest(endpoint, rawData, action);

}


function replaceDisplayElementAjaxRequest(
  endpoint, rawData, $display, callback = null
) {

  // The action is to replace the display element entirely
  function action(response) {
    $display.replaceWith(response);
    // Execute the callback function, if given
    if (callback != null) {
      callback();
    }
  }

  // Assign the response to the display object
  executeAjaxRequest(endpoint, rawData, action);

}


export { replaceDisplayContentsAjaxRequest, replaceDisplayElementAjaxRequest};
