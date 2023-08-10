/*
 * Show the transaction linked to the given transaction.
 *
 * Shows the two linked transactions overlayed over the transaction
 * table when the link icon is clicked for an expanded transaction.
 * The remainder of the screen is dimmed, and the two transactions
 * linked internally are shown in detail.
 */

import { executeAjaxRequest } from './modules/ajax.js';
import { OverlayManager } from './modules/manage-overlays.js';


(function() {

  const endpoint = LINKED_TRANSACTION_ENDPOINT;

  const $linkButton = $('img.link.button');
  const $container = $linkButton.parents('.transactions-container');
  const overlayManager = new OverlayManager($container);

  // Define the action to execute after executing the request
  function action(response) {
    overlayManager.addOverlay(response);
  }

  // Add AJAX request action to the link button
  $linkButton.on('click', function() {
    const transactionID = $(this).data("transaction-id");
    const rawData = {
      'transaction_id': transactionID,
    };
    executeAjaxRequest(endpoint, rawData, action);
  });

})();

