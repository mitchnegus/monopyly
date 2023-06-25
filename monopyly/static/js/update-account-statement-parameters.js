/*
 * Update the account statement dates of interest (due day/issue day).
 *
 * This script activates the database update widget. When a user clicks
 * the edit icon next to the account's statement due day or issue day,
 * the day becomes editable (an input box is displayed). This text box
 * completes an AJAX request when it loses focus. If the input is given
 * in an acceptable format, the new day is saved and the displayed day
 * is updated. If not, the existing statement due day or issue day in
 * the database is preserved and displayed.
 */

import { updateDBWidget } from './modules/update-database-widget.js';


(function() {

	const endpointDueDay = UPDATE_ACCOUNT_STATEMENT_DUE_DAY_ENDPOINT;
	const endpointIssueDay = UPDATE_ACCOUNT_STATEMENT_ISSUE_DAY_ENDPOINT;
	// Identify the key elements
	const $widgetDueDay = $('#statement-due-day.update-db-widget');
	const $widgetIssueDay = $('#statement-issue-day.update-db-widget');
	// Prepare the widget
	updateDBWidget(endpointDueDay, $widgetDueDay);
	updateDBWidget(endpointIssueDay, $widgetIssueDay);

})();
