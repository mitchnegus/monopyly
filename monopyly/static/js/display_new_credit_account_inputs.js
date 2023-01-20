/* Display inputs for a new credit account when collecting new credit card info.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  // Identify the account selection box for a new card
  let $inputAccount = $('form#card #account_info-account_id');
  let $inputBank = $('form#card #account_info-bank_info-bank_id');
  let $inputBankName = $('form#card #account_info-bank_info-bank_name');
  let $secondaryAccountInfo = $('form#card #secondary-account-info');
  let $secondaryBankInfo = $('form#card #secondary-bank-info');
  // Set the value for the 'New account'/'New bank' options
  const valueNewEntry = 0;
  const valueUnset = -1;

  $inputAccount.on('change', function() {
    inputChange(this, showBankInput, hideBankInput);
  });

  $inputBank.on('change', function() {
    inputChange(this, showBankNameInput, hideBankNameInput);
  });

  function inputChange(input, newValueCallback, otherCallback) {
    // Execute an action depending on the new value of the changed input
    const inputValue = $(input).val();
    if (inputValue == valueNewEntry) {
      newValueCallback();
    } else if (inputValue > valueNewEntry) {
      otherCallback();
    }
  }

  function showBankInput() {
    $inputBank.prop('disabled', false);
    $secondaryAccountInfo.removeClass('hidden');
  }

  function hideBankInput() {
    // Set the input bank field to be read only (it has been specified)
    hideBankNameInput();
    $inputBank.val(valueUnset);
    $inputBank.prop('disabled', true);
    $secondaryAccountInfo.addClass('hidden');
  }

  function showBankNameInput() {
    $inputBankName.prop('readonly', false);
    $secondaryBankInfo.removeClass('hidden');
  }

  function hideBankNameInput() {
    // Set the input bank name field to be read only (it has been specified)
    $inputBankName.val("");
    $inputBankName.prop('readonly', true);
    $secondaryBankInfo.addClass('hidden');
  }

  function setBankValue(value) {
    $inputBank.val(value);
  }

})();
