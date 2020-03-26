/*
 * Update the display of credit card statements.
 *
 * Update the display of credit card statements. The display update
 * issues an Ajax request to the server to query the database based on
 * the user's selection. Updates are triggered by changing the card
 * filters. A user can click on any of the card filters to show/hide
 * transactions from that card.
 */

import { updateDisplayAjaxRequest } from './modules/update_display_ajax.js';


(function() {

	// Identify the card filters
	let container = $('#statements-container');
	let filterContainer = $('#card-filter');
	
	// Send the Ajax request on click
	let filters = filterContainer.find('.card');
	filters.on('click', function() {
		// Add or remove the selected tag when clicked
		updateDisplay();
	});
	
	function updateDisplay() {
		// Determine the selected credit cards to use from the filters
		let selectedFilters = filterContainer.find('.card.selected');
		let filterIDs = [];
		selectedFilters.each(function() {filterIDs.push(this.id);});
		// Update the display with the filters
		let endpoint = FILTER_ENDPOINT;
		let rawData = {'filter_ids': filterIDs};
		updateDisplayAjaxRequest(endpoint, rawData, container);
	}
	
})();
