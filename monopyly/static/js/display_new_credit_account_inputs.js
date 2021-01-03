/* Display inputs for account information when collecting new credit card info.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

	// Identify the account selection box for a new card
	let $inputAccount = $('form#card #account_id');
	let $inputBank = $('form#card #bank_name');
	let $secondaryInfo = $('form#card #secondary-info');

	$inputAccount.on('change', function() {
		const $account = $(this).val();
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
		function inferenceAction(response) {
			$inputBank.val(response);
		}
		executeAjaxRequest(INFER_BANK_ENDPOINT, rawData, inferenceAction);
	}

})();
