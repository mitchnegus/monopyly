/* Display inputs for a new credit account when collecting new credit card info.
 */

import { AcquisitionFormManager } from './modules/manage-acquisition-form.js';


(function() {

  // Display the bank information inputs for a new account
  let $inputAccount = $('form#card #account_info-account_id');
  let $secondaryAccountInfo = $('form#card #secondary-account-info');

  const accountAcquisitionFormManager = new AcquisitionFormManager(
    $inputAccount,
    $secondaryAccountInfo,
  );

  // Display the bank name input box for the new bank
  let $inputBank = $('form#card #account_info-bank_info-bank_id');
  let $secondaryBankInfo = $('form#card #secondary-bank-info');

  const bankAcquisitionFormManager = new AcquisitionFormManager(
    $inputBank,
    $secondaryBankInfo,
  );

})();
