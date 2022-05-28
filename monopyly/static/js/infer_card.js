/* Infer card information if enough identifying info is provided.
 *
 * When entering a transaction, infer the remaining card information
 * based on the current set of provided information. After a user
 * finishes entering input in either of the two card information fields,
 * matching cards in the database are identified using an AJAX request.
 * If only one card matches the criteria, it is inferred and the
 * remaining information is populated.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  // Identify all input elements in the form
  const $inputElements = $('form input');
  // Identify inputs for card information
  const subformIDPrefix = '#statement_info-card_info_'
  const $inputBank = $inputElements.filter(subformIDPrefix + 'bank_name');
  const $inputDigits = $inputElements.filter(subformIDPrefix + 'last_four_digits');

  // Set triggers for checking about inferences
  $inputBank.on('blur', function() {
    const rawData = {'bank_name': $(this).val()};
    inferCardAjaxRequest(rawData);
  });
  $inputDigits.on('blur', function() {
    const rawData = {
      'bank_name': $inputBank.val(),
      'digits': $(this).val()
    };
    inferCardAjaxRequest(rawData);
  });

  function inferCardAjaxRequest(rawData) {
    // Return a single card matching the criteria of the raw data
    function inferenceAction(response) {
      if (response != '') {
        // A card can be inferred, so populate the fields with its info
        $inputBank.val(response['bank_name']);
        $inputDigits.val(response['digits']);
        const nextInputIndex = $inputElements.index($inputDigits[0])+1;
        $inputElements.eq(nextInputIndex).focus();
      }
    }
    executeAjaxRequest(INFER_CARD_ENDPOINT, rawData, inferenceAction);
  }

})();
