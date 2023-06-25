/*
 * Expand a row in a box-table.
 *
 * Expands a row in a table of boxes, when the box-row contains an element
 * with the 'expanded' class. This expanded elemente should initially have
 * its display style attribute set to 'none'.
 */


function toggleBoxRow($boxRow) {

  // Set timing variables
  const slideTime = 250;

  $boxRow.on('click', function(e) {
    // Ignore the click if it is on a button
    const $buttons = $(this).find(".icon-button");
    const $clickTarget = $(e.target)
    if (!$clickTarget.is($buttons)) {
      // Toggle the expanded box row
      const $expandedRow = $(this).find('.expanded');
      $expandedRow.slideToggle(slideTime);
    }
  });
}


export { toggleBoxRow };
