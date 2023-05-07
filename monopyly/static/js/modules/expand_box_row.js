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

  $boxRow.on('click', function() {
    // Show the expanded box row
    const $expandedRow = $(this).find('.expanded');
    $expandedRow.slideToggle(slideTime);
  });
}


export { toggleBoxRow };
