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
  replaceDisplayContentsAjaxRequest
} from './modules/update-display-ajax.js';
import { toggleTransactionRow } from './modules/expand-transaction.js';


function displaySubtransactions($transaction) {

    // Execute an AJAX request to get transaction/subtransaction information
    const endpoint = EXPAND_TRANSACTION_ENDPOINT;
    const rawData = $transaction.data("transaction-id");
    const $container = $transaction.find('.subtransaction-container');
    replaceDisplayContentsAjaxRequest(endpoint, rawData, $container);

}


(function() {

  toggleTransactionRow(displaySubtransactions);

})();
