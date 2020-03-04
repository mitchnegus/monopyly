/*
 * Update the display of credit card statements.
 *
 * Update the display of credit card statements. The display update
 * issues an Ajax request to the server to query the database based on
 * the user's selection. The Ajax request is defined in its own
 * function. Updates are triggered by changing the card filters. A user
 * can click on any of the card filters to show/hide transactions from
 * that card.
 */

(function() {

	// Identify the card filters
	var container = $('#statements-container');
	var filterContainer = $('#card-filter');
	
	// Send the Ajax request on click
	var filters = filterContainer.find('.card');
	filters.on('click', function() {
		// Add or remove the selected tag when clicked
		updateDisplay();
	});
	
	function updateDisplay() {
		// Determine the selected credit cards to use from the filters
		var selectedFilters = filterContainer.find('.card.selected');
		var filterIDs = [];
		selectedFilters.each(function() {filterIDs.push(this.id);});
		// Update the display with the filters
		updateDisplayAjaxRequest(filterIDs);
	}
	
	function updateDisplayAjaxRequest(filterIDs) {
		var rawData = {'filter_ids': filterIDs}
		// Return a filtered display for each ID in the set of filterIDs
		$.ajax({
			url: FILTER_ENDPOINT,
			type: 'POST',
			data: JSON.stringify(rawData),
			contentType: 'application/json; charset=UTF-8',
			success: function(response) {
				container.html(response);
			},
			error: function(xhr) {
				console.log('There was an error in the Ajax request.');
			}
		});
	}

})();
