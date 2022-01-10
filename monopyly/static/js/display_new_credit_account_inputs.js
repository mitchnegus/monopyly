/* Display inputs for a new credit account when collecting new credit card info.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  const endpoint = INFER_BANK_ENDPOINT;
  // Identify the account selection box for a new card
  let $inputAccount = $('form#card #account_id');
  let $inputBank = $('form#card #bank_name');
  let $secondaryInfo = $('form#card #secondary-info');
  // Set the value for the 'New account' option
  const valueNewAccount = 0;

  $inputAccount.on('change', function() {
    const $account = $(this).val();
    if ($account == valueNewAccount) {
      // Show the card input fields if the 'New account' option is chosen
      $inputBank.prop('readonly', false);
      $secondaryInfo.removeClass('hidden');
    } else if ($account > valueNewAccount) {
      // Set the input bank field to be read only (it was selected)
      $inputBank.prop('readonly', true);
      inferBankAjaxRequest($account);
      $secondaryInfo.addClass('hidden');
    }
  });

  function inferBankAjaxRequest($account) {
    const rawData = {'account_id': $account};
    // Return a the bank matching the account
    executeAjaxRequest(endpoint, rawData, setBankValue);
  }

  function setBankValue(value) {
    $inputBank.val(value);
  }

})();
