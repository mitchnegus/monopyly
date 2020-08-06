/*
 * Update an object with the results of an AJAX request.
 *
 * An object (`$display`) is updated using the response from an AJAX
 * request. The request delivers a set of data (`rawData`) to the given
 * endpoint. If nothing is returned, an error is logged. Various
 * functions are defined below to peform different actions using the
 * resuls of the request.
 */

function executeAjaxRequest(endpoint, rawData, action = function(){} ) {

	// Execute the action using the response of the AJAX request
	$.ajax({
		url: endpoint,
		type: 'POST',
		data: JSON.stringify(rawData),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			action(response);
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});

}


function replaceDisplayContentsAjaxRequest(endpoint, rawData, $display) {

	// The action is to replace the display's contents
	function action(response) {
		$display.html(response);
	}
	// Assign the response to the display object
	executeAjaxRequest(endpoint, rawData, action);

}


export { replaceDisplayContentsAjaxRequest, executeAjaxRequest };
