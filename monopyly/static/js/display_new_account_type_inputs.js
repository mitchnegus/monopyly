/* Display inputs for a new account type when collecting new bank account info.
 */

import { displayInput } from './modules/display_new_choice_form_input.js';


(function() {

  // Identify the account selection box for a new card
  let $fieldAccountTypeName = $('form#bank-account #account-type-name-field');
  let $inputAccountType = $('form#bank-account #account_type_info-account_type_id');
  displayInput(
    $fieldAccountTypeName,
    $inputAccountType
  );

})();
