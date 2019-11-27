/*
 * Update the table of credit card transactions.
 *
 * Update credit card transaction table. The table update uses an Ajax request
 * to the server to query the database based on the user's selection. The Ajax
 * request is defined in its own function.
 *
 * Updates can be triggered by the following actions:
 * 	- Changing the card filters: a user can click on any of the card
 * 	  filters to show or hide transactions from that card (inactive filters
 * 	  also display a label indicating their inactive status).
 * 	- Sorting the table by transaction date: a user can click on the 'Date'
 * 	  column header to sort the transaction date in ascending or descending
 *	  order.
 */

// Identify the card filters
var container = $('#transaction-table-container');
var filterContainer = $('#card-filter');

// Label inactive cards when they are hovered over
var inactiveCardFilters = filterContainer.find('.inactive.card');
var defaultText, defaultWidth;
inactiveCardFilters.hover(
	function () {
		var $this = $(this);
		defaultText = $this.text();
		defaultWidth = $this.width();
		// Change the text, maintain the width
		$this.text('Inactive Card');
		$this.width(defaultWidth);
	},
	function() {
		var $this = $(this);
		$this.text(defaultText);
	}
);

// Change the filter status and send the Ajax request on click
var filters = filterContainer.find('.card');
filters.on('click', function() {
	// Add or remove the selected tag when clicked
	$(this).toggleClass('selected')
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
	updateTableAjaxRequest(filterIDs, sortOrder);
	// Update the sorters since they have been replaced
	sorters = $('.sort-icon');
}

function updateTableAjaxRequest(filterIDs, sortOrder) {
	var rawData = {
		'filter_ids': filterIDs,
		'sort_order': sortOrder
	};
	// Return a filtered table for each ID in the set of filterIDs
	$.ajax({
		url: $TABLE_UPDATE_ENDPOINT,
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
