/*
 * Update a credit card statement's due date.
 *
 * This script activates the database update widget. When a user clicks
 * the edit icon next to the statement due date, the due date becomes
 * editable (an input box is displayed). This text box completes an AJAX
 * request when it loses focus. If the input is given in an acceptable
 * format, the new date is saved and the displayed due date is updated.
 * If not, the existing statement due date in the database is preserved
 * and displayed.
 */

import { updateDBWidget } from './modules/update-database-widget.js';


(function() {

	const endpoint = UPDATE_STATEMENT_DUE_DATE_ENDPOINT;
	// Identify the key elements
	const $widget = $('#due-date.update-db-widget');
	// Prepare the widget
	updateDBWidget(endpoint, $widget);

})();
