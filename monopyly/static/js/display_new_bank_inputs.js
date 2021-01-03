/* Display inputs for bank information when collecting new bank account info.
 */

(function() {

	// Identify the account selection box for a new card
	let $fieldBankName = $('form#bank-account #bank-name-field');
	let $inputBank = $('form#bank-account #bank_id');
	let $inputBankName = $('form#bank-account #bank_name');

	$inputBank.on('change', function() {
		const $account = $(this).val();
		if ($account == 0) {
			$inputBank.prop('readonly', false);
			$fieldBankName.removeClass('hidden');
		} else if ($account > 0) {
			$fieldBankName.addClass('hidden');
		}
	});

})();
