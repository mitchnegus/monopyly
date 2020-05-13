/* Display inputs for account information when collecting new card info.
 */

(function() {

	// Identify the account selection box for a new card
	let $inputAccount = $('form#card #account_id');
	let $inputBank = $('form#card #bank');
	let $secondaryInfo = $('form#card #secondary-info');

	$inputAccount.on('change', function() {
		$account = $(this).val();
		if ($account == 0) {
			$inputBank.prop('readonly', false);
			$secondaryInfo.removeClass('hidden');
		} else if ($account > 0) {
			$inputBank.prop('readonly', true);
			inferBankAjaxRequest($account)
			$secondaryInfo.addClass('hidden');
		}
	});

	function inferBankAjaxRequest($account) {
		let rawData = {'account_id': $account};
		// Return a the bank matching the account
		$.ajax({
			url: INFER_BANK_ENDPOINT,
			type: 'POST',
			data: JSON.stringify(rawData),
			contentType: 'application/json; charset=UTF-8',
			success: function(response) {
				$inputBank.val(response);
			},
			error: function(xhr) {
				console.log('There was an error in the Ajax request.');
			}
		});
	}

})();
