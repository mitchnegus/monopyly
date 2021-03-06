/*
 * Add a new subtransaction to a transaction form.
 *
 * Adds fields to the transaction form to allow the addition of a new
 * subtransaction. When the button is pressed to add a subtransaction, 
 * an AJAX request is executed to retrieve an extra set of subfields
 * for the transaction form. The AJAX request includes information about
 * the number of current subtransactions already being displayed, so
 * that new subtransaction fields may be indexed accordingly. The page
 * is updated with the new field information.
 */

import { executeAjaxRequest } from './modules/update_display_ajax.js';


(function() {

	const endpoint = ADD_SUBTRANSACTION_FORM_ENDPOINT;
	// Identify the button to add subtransaction entry forms
	const $button = $('#new-subtransaction.button'); 
	
	$button.on('click', function() {
		const subtransactionCount = $('.subtransaction-form').length
		// Execute the AJAX request to retrieve a new subtransaction form
		const rawData = {'subtransaction_count': subtransactionCount};
		function addSubtransactionForm(response) {
			// Add the new form at the end of the set of subtransaction forms
			$('#subtransactions').append(response);
		}
		executeAjaxRequest(endpoint, rawData, addSubtransactionForm);
	});

})();
