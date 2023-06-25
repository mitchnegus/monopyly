/*
 * Expand a bank account (on the 'Bank Accounts' page).
 *
 * Expands a bank account row in the bank account grouping for a given
 * bank when the row is clicked. The expanded row shows the options menu
 * for editing bank information (e.g., deleting the account). A user
 * can exit the expanded view by clicking anywhere within the expanded
 * view (that is not otherwise a button).
 */

import { toggleBoxRow } from './modules/expand-box-row.js';


(function() {

  // Identify the account rows
  const $accountRow = $('#bank-container .account-block');
  toggleBoxRow($accountRow);

})();
