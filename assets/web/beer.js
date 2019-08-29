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

    var colors = [
        "rgb(255, 87, 87)", // red
        "rgb(255, 171, 87)", // orange
        "rgb(255, 213, 87)", // orange clair
        "rgb(213, 255, 87)", // yellow
        "rgb(171, 255, 87)", // vert clair
        "rgb(87, 255, 87)", // vert
        "rgb(87, 255, 171)", // turquoise
        "rgb(87, 255, 255)", // cyan
        "rgb(87, 171, 255)", // bleu
        "rgb(87, 87, 255)", // indigo
        "rgb(171, 87, 255)", // purple
        "rgb(255, 87, 255)", // magenta
        "rgb(255, 87, 171)", // rose
        "rgb(128, 128, 128)", // grey
        "rgb(50, 55, 55)", // light grey
    ];

    datasets.forEach(function (item, index) {
        item.fill = false;
        item.backgroundColor = colors[index];
        item.borderColor = colors[index];
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
