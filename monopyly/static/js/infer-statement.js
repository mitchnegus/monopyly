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

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  // Identify all input elements in the form
  const $inputElements = $('form input');
  // Identify inputs for card information
  const subformIDPrefix = '#statement_info-card_info-'
  const $inputBank = $inputElements.filter(subformIDPrefix + 'bank_name');
  const $inputDigits = $inputElements.filter(subformIDPrefix + 'last_four_digits');
  const $inputTransactionDate = $inputElements.filter('#transaction_date');
  const $inputStatementDate = $inputElements.filter('#statement_info-issue_date');

  $inputTransactionDate.on('blur', function() {
    const rawData = {
      'bank_name': $inputBank.val(),
      'digits': $inputDigits.val(),
      'transaction_date': $inputTransactionDate.val()
    };
    inferStatementAjaxRequest(rawData);
  });

  function inferStatementAjaxRequest(rawData) {
    // Return a single statement matching the criteria of the raw data
    function inferenceAction(response) {
      if (response != '') {
        // A statement can be inferred, so populate the fields with its info
        $inputStatementDate.val(response);
        const nextInputIndex = $inputElements.index($inputTransactionDate[0])+1;
        $inputElements.eq(nextInputIndex).focus();
      }
    }
    executeAjaxRequest(INFER_STATEMENT_ENDPOINT, rawData, inferenceAction);
  }

})();
