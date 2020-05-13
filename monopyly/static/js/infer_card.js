/* Infer card information if enough identifying info is provided.
 *
 * When entering a transaction, infer the remaining card information
 * based on the current set of provided information. After a user
 * finishes entering input in either of the two card information fields,
 * matching cards in the database are identified using an AJAX request.
 * If only one card matches the criteria, it is inferred and the
 * remaining information is populated.
 */

(function() {

	// Identify all input elements in the form
	const $inputElements = $('form input');
	// Identify inputs for card information
	const $inputBank = $inputElements.filter('input#bank');
	const $inputDigits = $inputElements.filter('input#last_four_digits');
	
	// Set triggers for checking about inferences
	$inputBank.on('blur', function() {
		const rawData = {'bank': $(this).val()};
		inferCardAjaxRequest(rawData);
	});
	$inputDigits.on('blur', function() {
		const rawData = {
			'bank': $inputBank.val(),
			'digits': $(this).val()
		};
		inferCardAjaxRequest(rawData);
	});
	
	function inferCardAjaxRequest(rawData) {
		// Return a single card matching the criteria of the raw data
		$.ajax({
			url: INFER_CARD_ENDPOINT,
			type: 'POST',
			data: JSON.stringify(rawData),
			contentType: 'application/json; charset=UTF-8',
			success: function(response) {
				if (response != '') {
					// A card can be inferred, so populate the fields with its info
					$inputBank.val(response['bank']);
					$inputDigits.val(response['digits']);
					const nextInputIndex = $inputElements.index($inputDigits[0])+1;
					$inputElements.eq(nextInputIndex).focus();
				}
			},
			error: function(xhr) {
				console.log('There was an error in the Ajax request.');
			}
		});
	}

})();
