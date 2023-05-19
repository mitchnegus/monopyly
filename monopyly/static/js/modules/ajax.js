/*
 * Provide a function to execute AJAX requests.
 */

/**
 * Execute an AJAX request.
 *
 * @param {string} endpoint - The endpoint URL where the request will be sent.
 * @param {Object} rawData - The button that adds a subform.
 * @callback action - The action to be taken after receiving the response.
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

