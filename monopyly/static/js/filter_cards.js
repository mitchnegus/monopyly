/*
 * Filter transactions by selected/unselected credit cards.
 *
 * First, add CSS to indicate which cards are selected or unselected. Then,
 * define a function pointing to a route which executes a database query for
 * only the selected cards.
 */

var filterContainer = $("#card-filter");
var filters = filterContainer.find(".card");

function filterAjaxRequest(filterIDs) {
	// Return a filtered table for each ID in the set of filterIDs
	$.ajax({
		url: $FILTER_SCRIPT,
		type: "POST",
		data: JSON.stringify(filterIDs),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			container = $('#transaction-table-container');
			container.html(response);
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});
}

filters.on("click", function() {
	// Add or remove the selected tag when clicked
	if (this.className.includes("selected")) {
		this.className = this.className.replace(" selected", "");
	} else {
		this.className += " selected";
	}
	// Update the page with only the selected card transactions
	var selectedFilters = filterContainer.find(".card.selected")
	var filterIDs = []
	selectedFilters.each(function() {filterIDs.push(this.id);});
	filterAjaxRequest(filterIDs);
});
