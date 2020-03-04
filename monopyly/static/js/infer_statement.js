/*
 * Infer credit card statement if enough identifying info is provided.
 *
 * When entering a transaction, infer the statement on which the 
 * transaction belongs based on the current set of provided information.
 * After a user finishes entering the transaction date, that date and
 * the two card information field values are used to identify matching
 * statements in the database using an AJAX request. If only one
 * statement matches the criteria, it is inferred and the statement
 * issue date field is populated.
 */

(function() {

	// Identify all input elements in the form
	let $inputElements = $('form input');
	// Identify inputs for card information
	let $inputBank = $inputElements.filter('input#bank');
	let $inputDigits = $inputElements.filter('input#last_four_digits');
	let $inputTransactionDate = $inputElements.filter('input#transaction_date');
	let $inputStatementDate = $inputElements.filter('input#issue_date');
	
	$inputTransactionDate.on('blur', function() {
		inferStatementAjaxRequest();
	});
	
	function inferStatementAjaxRequest() {
		// Return a single statement matching the criteria of the raw data
		let rawData = {
			'bank': $inputBank.val(),
			'digits': $inputDigits.val(),
			'transaction_date': $inputTransactionDate.val()
		};
		$.ajax({
			url: INFER_STATEMENT_ENDPOINT,
			type: 'POST',
			data: JSON.stringify(rawData),
			contentType: 'application/json; charset=UTF-8',
			success: function(response) {
				if (response != '') {
					// A statement can be inferred, so populate the fields with its info
					$inputStatementDate.val(response);
					let nextInputIndex = $inputElements.index($inputTransactionDate[0])+1;
					$inputElements.eq(nextInputIndex).focus();
				}
			},
			error: function(xhr) {
				console.log('There was an error in the Ajax request.');
			}
		});
	}

})();
