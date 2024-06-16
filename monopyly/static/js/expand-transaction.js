/*
 * Expand a transaction in a table when the plus icon is clicked.
 *
 * Expands a row in the transaction table when the plus icon offering
 * more information is clicked. The expanded row shows transactions in
 * more detail (and a larger font) than the rest of the transaction
 * table. For both credit card and bank transactions, this expanded row
 * shows subtransaction information.
 */

import {
  TransactionToggleManager, displaySubtransactions
} from './modules/expand-transaction.js';


(function() {
  const toggleManager = new TransactionToggleManager(displaySubtransactions)
  // For mobile layouts, expand transactions when the row is clicked
  if (window.innerWidth <= 600) {
    const $transactions = $('.transaction');
    $transactions.on('click', function(event) {
      if (!this.classList.contains('selected')) {
        const $transactionExpandButton = $(this).find('.more.button');
        $transactionExpandButton.trigger('click');
      }
    });
  }
})();
