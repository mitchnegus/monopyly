/*
 * Prepare a donut chart of category subtotals using the `chartist.js` library.
 *
 * Creates a donut chart using data (provided in the HTML template) for
 * transaction categories based on their subtotals.
 */


function createCategoryChart(data) {

  const options = {
    donut: true,
    donutWidth: 40,
    chartPadding: 40,
    labelOffset: 50,
    labelDirection: "explode"
  };
  new Chartist.PieChart("#category-chart", data, options);

}


(function() {

  createCategoryChart(CATEGORY_CHART_DATA);

})();
