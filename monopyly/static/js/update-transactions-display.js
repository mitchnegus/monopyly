/*
 * Update the table of credit card transactions.
 *
 * Update the credit card transaction table. The table update issues an
 * Ajax request to the server to query the database based on the user's
 * selection. The Ajax request is defined in its own function.
 *
 * Updates can be triggered by the following actions:
 *  - Changing the card filters: a user can click on any of the card
 *    filters to show or hide transactions from that card.
 *  - Sorting the table by transaction date: a user can click on the
 *    'Date' column header to sort the transaction date in ascending
 *    or descending order.
 */

import {
  TransactionToggleManager, displaySubtransactions
} from './modules/expand-transaction.js';
import {
  replaceDisplayElementAjaxRequest
} from './modules/update-display-ajax.js';


(function() {

  // Identify the card filters
  const $filterContainer = $('#card-filter');
  // Identify the transactions container
  const $container = $('.transactions-container');
  // Identify selectors used when loading additional transactions
  const selectors = LOAD_TRANSACTIONS_SELECTORS;

  // Send the Ajax request on click
  const $filters = $filterContainer.find('.card');
  $filters.on('click', function() {
    updateTable();
  });

  // Change the table ordering and send the Ajax request on click
  $container.on('click', '.transactions-table .sort-button', function() {
    // Identify the table sorters
    const $sorters = $('.transactions-table .sort-button');
    // Swap the sorter icons
    $sorters.toggleClass('selected');
    // Update the table
    updateTable();
  });

  function updateTable() {
    // Determine the selected credit cards to use from the filters
    const $selectedFilters = $filterContainer.find('.card.selected');
    const cardIDs = [];
    $selectedFilters.each(function() {cardIDs.push(this.dataset.cardId);});
    // Determine the table ordering (ascending/descending transaction date)
    const $sorter = $('.transactions-table .sort-button.selected');
    let sortOrder
    if ($sorter.hasClass('asc')) {
      sortOrder = 'asc';
    } else {
      sortOrder = 'desc';
    }
    // Update the table with the filters and ordering
    const $table = $container.find('.transactions-table');
    const endpoint = FILTER_ENDPOINT;
    const rawData = {
      'card_ids': cardIDs,
      'sort_order': sortOrder,
    };

    function callback() {
      const toggleManager = new TransactionToggleManager(displaySubtransactions)
    }
    replaceDisplayElementAjaxRequest(endpoint, rawData, $table, callback)
    // Update the selectors with the new filters and ordering
    selectors["selected_card_ids"] = cardIDs;
    selectors["sort_order"] = sortOrder;
  }

})();
