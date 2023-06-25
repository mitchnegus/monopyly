/* Display inputs for a new bank name when collecting new bank account info.
 */

import { AcquisitionFormManager } from './modules/manage-acquisition-form.js';


(function() {

  // Display the bank name input box for the new bank
  let $inputBank = $('form#bank-account #bank_info-bank_id');
  let $fieldBankName = $('form#bank-account #bank-name-field');

  const bankAcquisitionFormManager = new AcquisitionFormManager(
    $inputBank,
    $fieldBankName,
  );

})();
