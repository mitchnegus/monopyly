/* Display inputs for a new bank name when collecting new bank account info.
 */

import { displayInput } from './modules/display_new_choice_form_input.js';


(function() {

  // Display the bank name input box for the new bank
  let $inputBank = $('form#bank-account #bank_info-bank_id');
  let $fieldBankName = $('form#bank-account #bank-name-field');
  displayInput(
    $inputBank,
    $fieldBankName,
  );

})();
