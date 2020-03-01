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
let $editButton = $('#edit-due-date-icon');
let $dueDate = $('#statement-info #payment #due #due-date');
let $dueDateInput = $('#statement-info #payment #due #edit-due-date');

$editButton.on('click', function() {
	// Hide the edit button while editing
	$editButton.hide();
	// Allow the user to enter a due date
	$dueDate.hide();
	$dueDateInput.show();
	$dueDateInput[0].select();
	// Set the text of the input to match the set due date
	$dueDateInput.val($dueDate.html());
	// Bind the enter key to blur
	$dueDateInput.on('keydown', function(event) {
		if (event.which == 13) {
				event.preventDefault();
				$dueDateInput.blur();
		}
	});
});

$dueDateInput.on('blur', function() {
	// Show the edit button (on hover) when not editing
	$editButton.show();
	// Hide the input box and show the database due date
	$dueDateInput.hide();
	$dueDate.show();
	// Execute an AJAX request to update the database
	updateStatementDueDateAjaxRequest();
	// Unbind the enter key
	$dueDateInput.off('keydown');
});

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
