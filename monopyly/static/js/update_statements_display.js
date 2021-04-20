/*
 * Update the display of credit card statements.
 *
 * Update the display of credit card statements. The display update
 * issues an Ajax request to the server to query the database based on
 * the user's selection. Updates are triggered by changing the card
 * filters. A user can click on any of the card filters to show/hide
 * transactions from that card.
 */

import {
  replaceDisplayContentsAjaxRequest
} from './modules/update_display_ajax.js';


(function() {

  // Identify the card filters
  const $filterContainer = $('#card-filter');
  // Identify the statements container
  const $container = $('#credit-statements-container');

  // Send the Ajax request on click
  const $filters = $filterContainer.find('.card');
  $filters.on('click', function() {
    // Add or remove the selected tag when clicked
    replaceDisplay();
  });

  function replaceDisplay() {
    // Determine the selected credit cards to use from the filters
    const $selectedFilters = $filterContainer.find('.card.selected');
    const filterIDs = [];
    $selectedFilters.each(function() {filterIDs.push(this.id);});
    // Update the display with the filters
    const endpoint = FILTER_ENDPOINT;
    const rawData = {'filter_ids': filterIDs};
    replaceDisplayContentsAjaxRequest(endpoint, rawData, $container);
  }

})();
