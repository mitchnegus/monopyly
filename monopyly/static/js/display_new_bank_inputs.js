/* Display inputs for a new bank name when collecting new bank account info.
 */

import { displayInput } from './modules/display_new_choice_form_input.js';


(function() {

  // Identify the account selection box for a new card
  let $fieldBankName = $('form#bank-account #bank-name-field');
  let $inputBank = $('form#bank-account #bank_info-bank_id');
  displayInput(
    $fieldBankName,
    $inputBank
  );

})();
