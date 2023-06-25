/*
 * Expand a bank (on the 'Profile' page).
 *
 * Expands a bank row in the bank list for a given bank when the row
 * is clicked. The expanded row shows the options menu for editing
 * bank information (e.g., updating or deleting the bank). A user can
 * can exit the expanded view by clicking anywhere within the expanded
 * view (that is not otherwise a button).
 */

import { toggleBoxRow } from './modules/expand-box-row.js';


(function() {

  // Identify the bank rows
  const $bankRow = $('.bank-list .bank-block');
  toggleBoxRow($bankRow);

})();
