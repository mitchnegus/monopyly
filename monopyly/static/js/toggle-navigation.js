/* Toggle the navigation menu for mobile views.
 */

(function() {

  // Identify the navigation menu and icon
  const $menu = $('#header-menu');
  const $menuLinks = $menu.find(".menu-links")
  const $toggleButton = $menu.find('.toggle-button');


  $(document).on('click', function(event) {
    const targetIsToggleButton = $(event.target).closest($toggleButton).length;
    const targetIsMenu = $(event.target).closest($menuLinks).length;
    const mobileMenuIsActive = $toggleButton.hasClass('active');
    if (targetIsToggleButton || ! targetIsMenu && mobileMenuIsActive) {
      // Toggle the (vertical) navigation menu on/off when the button is clicked
      // (clicking outside the menu returns the menu to its original state)
      toggleMenu($toggleButton, $menuLinks);
    }
  });

})();


function toggleMenu($toggleButton, $menuLinks) {
  $menuLinks.slideToggle({
    duration: 300,
    start: function() {
      $(this).css('display', 'flex');
    },
  });
  $toggleButton.toggleClass('active');
}

