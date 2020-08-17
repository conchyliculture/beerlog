function update_graph(path, func) {
	var xhttp = new XMLHttpRequest(), method = "GET", url=path;
	xhttp.onreadystatechange = function() {
    	if (this.readyState == 4 && this.status == 200) {
            info = JSON.parse(xhttp.responseText);
            func(info['data']);
		}
	};
	xhttp.open(method, url, true);
	xhttp.send();
}
function drawChart(le_data) {
    console.log(le_data);
    var labels = le_data['labels'];
    var datasets = le_data['datasets']
    console.log(datasets);

    datasets.forEach(function (item, index) {
        var color = "hsl(" + (360.0 * index / datasets.length) + ", 50%, 50%)";
        item.fill = false;
        item.backgroundColor = color;
        item.borderColor = color;
    });

    var ctx = document.getElementById('myChart').getContext('2d');

    var chart = new Chart(ctx, {
        // The type of chart we want to create
        type: 'line',

        // The data for our dataset
        data: {
            labels: labels,
            datasets: datasets
        },

        // Configuration options go here
        options: {}
    });
}
