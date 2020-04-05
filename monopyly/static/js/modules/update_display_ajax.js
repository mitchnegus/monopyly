/*
 * Update an on-screen object with the results of an AJAX request.
 *
 * An object (`$display`) has it's contents replaced by the response from
 * an AJAX request. The request delivers a set of data (`rawData`) to
 * the given endpoint. If nothing is returned, an error is logged.
 */

function updateDisplayAjaxRequest(endpoint, rawData, $display) {

	// Return the newly updated value and assign it to the display object
	$.ajax({
		url: endpoint,
		type: 'POST',
		data: JSON.stringify(rawData),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			$display.html(response);
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});

}

export { updateDisplayAjaxRequest };
