/*
 * Load more transactions when the plus icon is clicked.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  const endpoint = LOAD_TRANSACTIONS_ENDPOINT;
  const rawData = LOAD_TRANSACTIONS_SELECTORS;

  $("#more-transactions.button").on("click", function() {
    let $button = $(this);
    let $container = $button.closest(".transactions-container");
    let $table = $container.find(".transactions-table");
    rawData["block_count"] += 1;
    executeAjaxRequest(endpoint, rawData, function(response) {
      if (response) {
        $table.append(response);
      } else {
        console.log("no response");
      }
    });
  });

})();
