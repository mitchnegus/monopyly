/*
 * Update the day of the month when an account's statements are due.
 *
 * This script activates the database update widget. When a user clicks
 * the edit icon next to the account's statement due day, the day
 * becomes editable (an input box is displayed). This text box completes
 * an AJAX request when it loses focus. If the input is given in an
 * acceptable format, the new day is saved and the displayed due day is
 * updated. If not, the existing statement due day in the database is
 * preserved and displayed.
 */

import { updateDBWidget } from './modules/update_database_widget.js';


(function() {

	const endpoint = UPDATE_ACCOUNT_STATEMENT_DUE_DAY_ENDPOINT;
	// Identify the key elements
	const $widget = $('#statement-due-day.update-db-widget');

	updateDBWidget(endpoint, $widget);
	
})();
