/*
 * Update a credit card statement's due date.
 *
 * When a user clicks the `edit-due-date` icon on the statemeent details
 * page, this script changes the displayed due date into a text box
 * where a user can edit the date. The text box completes an AJAX
 * request when it loses focus, and if the input is given in an
 * acceptable format, the new date is saved and the displayed due date
 * is updated. If not, the existing statement due date in the database
 * is preserved and displayed.
 */

import { updateWidget } from './modules/update_database_widget.js';


(function() {

	let endpoint = UPDATE_STATEMENT_DUE_DATE_ENDPOINT;
	// Identify the key elements
	let $buttonEdit = $('#edit-due-date-icon');
	let $displayDueDate = $('#statement-info #payment #due #due-date');
	let $inputDueDate = $('#statement-info #payment #due #edit-due-date');

	updateWidget(endpoint, $buttonEdit, $displayDueDate, $inputDueDate);
	
})();
