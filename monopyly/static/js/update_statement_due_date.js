/*
 * Update a credit card statement's due date.
 *
 * When a user clicks the `edit-due-date` icon on the statemeent details
 * page, this script changes the displayed due date into a text box
 * where a user can edit the date. The text box completes an AJAX
 * request when the save button is pressed, and if the input is given
 * in an acceptable format, the new date is saved.
 */

// Identify the key elements
let $editButton = $('#edit.due-date-icon');
let $saveButton = $('#save.due-date-icon');
let $dueDate = $('#statement-info #payment #due #due-date');
let $dueDateInput = $('#statement-info #payment #due #edit-due-date');

$editButton.on('click', function() {
	toggleEditableDueDate();
	// Set the text of the input to match the set due date
	$dueDateInput.val($dueDate.html());
});

$saveButton.on('click', function() {
	toggleEditableDueDate();
	updateStatementDueDateAjaxRequest();
});

function toggleEditableDueDate() {
	// Swap the "Edit" and "Save" buttons
	$editButton.toggle();
	$saveButton.toggle();
	// Allow the user to enter a due date
	$dueDate.toggle();
	$dueDateInput.toggle();
}

// Identify inputs for card information

function updateStatementDueDateAjaxRequest() {
	// Return the newly updated statement date
	$.ajax({
		url: UPDATE_STATEMENT_DUE_DATE_ENDPOINT,
		type: 'POST',
		data: JSON.stringify($dueDateInput.val()),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			$dueDate.html(response)
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});
}
