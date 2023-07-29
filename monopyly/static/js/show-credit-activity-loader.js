/*
 * Show the modal for loading credit activity.
 *
 * Shows the overlay that gives a user the ability to upload a
 * file containing credit activity for comparison against the
 * current statement.
 */

import { executeAjaxRequest } from "./modules/ajax.js";
import { OverlayManager } from "./modules/manage-overlays.js";


(function() {

  const $linkButton = $("#reconciliation-button");
  const $container = $(".details[id^='credit-'][id$='-details']");
  const overlayManager = new OverlayManager($container);

  // Define the action to execute after executing the request
  function action(response) {
    overlayManager.addOverlay(response);
  }

  // Add AJAX request action to the link button
  $linkButton.on("click", function() {
    $.get(CREDIT_ACTIVITY_RECONCILIATION_ENDPOINT, action);
  });

})();
