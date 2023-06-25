/* Display inputs for a new account type when collecting new bank account info.
 */

import { AcquisitionFormManager } from './modules/manage-acquisition-form.js';


(function() {

  // Display the bank account type name input box for the new account type
  let $inputAccountType = $('form#bank-account #account_type_info-account_type_id');
  let $fieldAccountTypeName = $('form#bank-account #account-type-name-field');

  const accountTypeAcquisitionFormManager = new AcquisitionFormManager(
    $inputAccountType,
    $fieldAccountTypeName,
  );

})();
