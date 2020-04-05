/*
 * Update a credit card's status (active/inactive).
 *
 * This script updates the card's active status. When a user uses the
 * toggle switch on the back of a credit card, the card's status can be
 * selected as either 'Active' or 'Inactive'. Toggling the option
 * completes an AJAX request. The status is updated in the database and
 * the card is given a class of inactive.
 */

import { updateDisplayAjaxRequest } from './modules/update_display_ajax.js';


(function() {

	let endpoint = UPDATE_CARD_STATUS_ENDPOINT;
	// Identify the key elements
	let $switches = $('.toggle-switch-gadget');

	// Send an AJAX request when the switch is toggled
	$switches.on('change', function() {
		let $toggleSwitch = $(this);
		let $card = $toggleSwitch.closest('.credit-card');
		let $cardFront = $card.find('.card-face.front');
		let $checkbox = $toggleSwitch.find('input[type="checkbox"]');
		let cardActive = $checkbox.is(':checked');
		let rawData = {
			'input_id': $checkbox[0].id,
			'active': cardActive
		};
		updateDisplayAjaxRequest(endpoint, rawData, $cardFront);
		if (cardActive) {
			$card.removeClass('inactive');
		} else {
			$card.addClass('inactive');
		}
	});

})();
