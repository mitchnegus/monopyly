/*
 * Update the table of credit card transactions.
 *
 * Update the credit card transaction table. The table update issues an
 * Ajax request to the server to query the database based on the user's
 * selection. The Ajax request is defined in its own function.
 *
 * Updates can be triggered by the following actions:
 * 	- Changing the card filters: a user can click on any of the card
 * 	  filters to show or hide transactions from that card.
 * 	- Sorting the table by transaction date: a user can click on the
 * 	  'Date' column header to sort the transaction date in ascending
 * 	  or descending order.
 */

import { updateDisplayAjaxRequest } from './modules/update_display_ajax.js';


(function() {

	// Identify the card filters
	var container = $('#transactions-table-container');
	var filterContainer = $('#card-filter');
	
	// Send the Ajax request on click
	var filters = filterContainer.find('.card');
	filters.on('click', function() {
		updateTable();
	});
	
	// Change the table ordering and send the Ajax request on click
	var sorters;
	container.on('click', 'img.sort-icon', function() {
		sorters = $('img.sort-icon');
		// Swap the sorter icons
		sorters.toggleClass('selected');
		// Update the table
		updateTable();
	});
	
	function updateTable() {
		// Determine the selected credit cards to use from the filters
		var selectedFilters = filterContainer.find('.card.selected');
		var filterIDs = [];
		selectedFilters.each(function() {filterIDs.push(this.id);});
		// Determine the table ordering (ascending/descending transaction date)
		var sortOrder;
		var sorter = $('.sort-icon.selected');
		if (sorter.hasClass('asc')) {
			sortOrder = 'asc';
		} else {
			sortOrder = 'desc';
		}
		// Update the table with the filters and ordering
		let endpoint = FILTER_ENDPOINT;
		let rawData = {
			'filter_ids': filterIDs,
			'sort_order': sortOrder
		};
		updateDisplayAjaxRequest(endpoint, rawData, container);
		// Update the sorters since they have been replaced
		sorters = $('.sort-icon');
	}
	
})();