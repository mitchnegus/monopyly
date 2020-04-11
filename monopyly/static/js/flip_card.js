/* Flip a credit card when clicked to show content on back.
 *
 * Add a 'flipped' class to a credit card, displaying content on the
 * back of the card. After a user leaves the card "container", the card
 * flips back to its front (as it was originally displayed).
 */

(function() {

	// Identify the cards
	const $cards = $('.credit-card');

	// Add the flipped class to clicked cards
	$cards.on('click', function() {
		$(this).addClass('flipped');
	});

	// Remove the flipped class after clicking outside of a card
	$('html').on('click', function(event) {
		const $target = $(event.target);
		if (!$target.closest($cards).length) {
			$cards.removeClass('flipped');
		}
	});

})();
