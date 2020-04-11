/*
 * Update the day of the month when an account's statements are issued.
 *
 * This script activates the database update widget. When a user clicks
 * the edit icon next to the account's statement issue day, the day
 * becomes editable (an input box is displayed). This text box completes
 * an AJAX request when it loses focus. If the input is given in an
 * acceptable format, the new day is saved and the displayed issue day
 * is updated. If not, the existing statement issue day in the database
 * is preserved and displayed.
 */

import { updateDBWidget } from './modules/update_database_widget.js';


(function() {

	const endpoint = UPDATE_ACCOUNT_STATEMENT_ISSUE_DAY_ENDPOINT;
	// Identify the key elements
	const $widget = $('#statement-issue-day.update-db-widget');

	updateDBWidget(endpoint, $widget);
	
})();
