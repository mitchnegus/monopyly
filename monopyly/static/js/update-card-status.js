/*
 * Update a credit card's status (active/inactive).
 *
 * This script updates the card's active status. When a user uses the
 * toggle switch on the back of a credit card, the card's status can be
 * selected as either 'Active' or 'Inactive'. Toggling the option
 * completes an AJAX request. The status is updated in the database and
 * the card is given a class of inactive.
 */

import {
  replaceDisplayContentsAjaxRequest
} from "./modules/update-display-ajax.js";


(function() {

  const endpoint = UPDATE_CARD_STATUS_ENDPOINT;
  // Identify the key elements
  const $switches = $(".toggle-switch-gadget");

  // Send an AJAX request when the switch is toggled
  $switches.on("change", function() {
    const $toggleSwitch = $(this);
    const $card = $toggleSwitch.closest(".credit-card");
    const $cardFront = $card.find(".card-face.front");
    const $checkbox = $toggleSwitch.find('input[type="checkbox"]');
    const cardActive = $checkbox.is(":checked");
    const cardID = $checkbox.data("card-id");
    const rawData = {
      "card_id": cardID,
      "active": cardActive,
    };
    replaceDisplayContentsAjaxRequest(endpoint, rawData, $cardFront);
    if (cardActive) {
      $card.removeClass("inactive");
    } else {
      $card.addClass("inactive");
    }
  });

})();
