/*
 * Hide the homepage block when the 'x' button is clicked.
 */


(function() {

  const $homepageBlock = $("#homepage-block");
  const $hideButton = $homepageBlock.find(".hide.button");

  // Hide the homepage block when the button is clicked
  $hideButton.on("click", function() {
    $homepageBlock.animate({opacity: 0});
    $homepageBlock.animate(
      {height: 0, margin: 0, padding: 0},
      function() {$(this).remove()},
    );
    $.get(HIDE_HOMEPAGE_BLOCK_ENDPOINT);
  });

})();
