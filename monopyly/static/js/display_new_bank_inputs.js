/* Display inputs for bank information when collecting new bank account info.
 */

(function() {

	// Identify the account selection box for a new card
	let $fieldBankName = $('form#bank-account #bank-name-field');
	let $inputBank = $('form#bank-account #bank_id');
	let $inputBankName = $('form#bank-account #bank_name');
	// Set the value for the `New bank` option
	const valueNewBank = 0;

	$inputBank.on('change', function() {
		const $account = $(this).val();
		if ($account == valueNewBank) {
			// Show the bank input field if the 'New bank' option is chosen
			$fieldBankName.removeClass('hidden');
		} else if ($account > 0) {
			$fieldBankName.addClass('hidden');
		}
	});

})();
