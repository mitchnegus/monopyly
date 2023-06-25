/* Flip a credit card when clicked to show content on back.
 *
 * Add a 'flipped' class to a credit card, displaying content on the
 * back of the card. After a user leaves the card "container", the card
 * flips back to its front (as it was originally displayed).
 */

(function() {

	// Identify the cards
	const $cards = $('.credit-card');

	// Toggle the flipped class to clicked cards
	$cards.on('click', function() {
		$(this).toggleClass('flipped');
	});

	// Remove the flipped class after clicking on/outside of a card
	$('html').on('click', function(event) {
		const $target = $(event.target);
		const onCard = $target.closest($cards).length;
		if (!onCard) {
			$cards.removeClass('flipped');
		}
	});

})();
