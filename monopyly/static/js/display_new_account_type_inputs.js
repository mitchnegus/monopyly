/* Display inputs for a new account type when collecting new bank account info.
 */

import { displayInput } from './modules/display_new_choice_form_input.js';


(function() {

  // Display the bank account type name input box for the new account type
  let $inputAccountType = $('form#bank-account #account_type_info-account_type_id');
  let $fieldAccountTypeName = $('form#bank-account #account-type-name-field');
  displayInput(
    $inputAccountType,
    $fieldAccountTypeName,
  );

})();
