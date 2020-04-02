/* Flip a credit card when clicked to show content on back.
 *
 * Add a 'flipped' class to a credit card, displaying content on the
 * back of the card. After a user leaves the card "container", the card
 * flips back to its front (as it was originally displayed).
 */

(function() {

	// Identify the card container and the cards
	let $container = $('.cards-container');
	let $cards = $('.credit-card');

	// Add the flipped class to clicked cards
	$cards.on('click', function() {
		$(this).toggleClass('flipped');
	});

	// Remove the flipped class when the mouse leaves the card container
	$container.on('mouseleave', function() {
		$cards.removeClass('flipped');
	});

})();
