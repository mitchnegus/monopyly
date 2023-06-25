/*
 * Update the bank name.
 *
 * This script activates the database update widget. When a user clicks
 * the edit icon under the bank's name, the name becomes editable (an
 * input box is displayed). This text box completes an AJAX request when
 * it loses focus. If the input is given in an acceptable format, the new
 * day is saved and the displayed day is updated. If not, the existing
 * statement due day or issue day in the database is preserved and
 * displayed.
 */

import { updateDBWidget } from './modules/update-database-widget.js';


(function() {

  const endpoints = UPDATE_BANK_NAME_ENDPOINTS;
  // Identify the key elements
  const $widgets = $('#profile .bank-block.update-db-widget');
  $widgets.each(function() {
    const $widget = $(this);
    const bankID = $widget.data("bank-id");
    const endpoint = endpoints[bankID]
    // Prepare the widget
    updateDBWidget(endpoint, $widget);
  });

})();
