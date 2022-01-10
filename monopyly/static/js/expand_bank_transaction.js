/*
 * Expand a bank account transaction when the plus icon is clicked.
 *
 * Expands a row in the transaction table when the plus icon offering
 * more information is clicked. The expanded row shows transactions in
 * more detail (and a larger font) than the rest of the transaction
 * table. For bank accounts, this expanded row shows ...
 */

import { toggleTransactionRow } from './modules/expand_transaction.js';


(function() {

  toggleTransactionRow();

})();
