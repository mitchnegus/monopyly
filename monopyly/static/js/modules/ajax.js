/*
 * Provide a function to execute AJAX requests.
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

export { executeAjaxRequest };

