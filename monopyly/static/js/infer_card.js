/*
 * Infer card information if enough identifying info is provided.
 *
 * When entering a transaction, infer the remaining card information
 * based on the current set of provided information. After a user
 * finishes entering input in either of the two card information fields,
 * matching cards in the database are identified using an AJAX request.
 * If only one card matches the criteria, it is inferred and the
 * remaining information is populated.
 */

// Identify all input elements in the form
var $inputElements = $('form input');
// Identify inputs for card information
var $bankInput = $inputElements.filter('input#bank');
var $digitsInput = $inputElements.filter('input#last_four_digits');

// Set triggers for checking about inferences
$bankInput.on('blur', function() {
	var rawData = {'bank': $(this).val()};
	inferCardAjaxRequest(rawData);
});
$digitsInput.on('blur', function() {
	var rawData = {
		'bank': $bankInput.val(),
		'digits': $(this).val()
	};
	inferCardAjaxRequest(rawData);
});

function inferCardAjaxRequest(rawData) {
	// Return a single card matching the criteria of the raw data
	$.ajax({
		url: $INFER_CARD_ENDPOINT,
		type: 'POST',
		data: JSON.stringify(rawData),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			if (response != '') {
				// A card can be inferred, so populate the fields with its info
				$bankInput.val(response['bank']);
				$digitsInput.val(response['digits']);
				var nextInputIndex = $inputElements.index($digitsInput[0])+1;
				$inputElements.eq(nextInputIndex).focus();
			}
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});
}
