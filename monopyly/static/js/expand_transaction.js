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
} from './modules/update_display_ajax.js';
import { toggleTransactionRow } from './modules/expand_transaction.js';


function display_subtransactions($transaction) {

    // Execute an AJAX request to get transaction/subtransaction information
    const endpoint = EXPAND_TRANSACTION_ENDPOINT;
    const rawData = $transaction[0].id;
    const $container = $transaction.find('.subtransaction-container');
    replaceDisplayContentsAjaxRequest(endpoint, rawData, $container);

}

(function() {

  toggleTransactionRow(display_subtransactions);

})();
