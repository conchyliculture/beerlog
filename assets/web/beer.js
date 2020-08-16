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
    var datasets = le_data['datasets'];
    var drinkers = le_data['drinkers'];
    console.log(datasets);

    // Assign a color for each name.
    var nameToColor = {};
    for (var idx in drinkers) {
      nameToColor[drinkers[idx]] = "hsl(" + (360.0 * idx / drinkers.length) + ", 50%, 50%)";
    }

    var ctx = document.getElementById('myChart').getContext('2d');

    datasets.forEach(function (item) {
        item.backgroundColor = nameToColor[item.label];
        item.borderColor = nameToColor[item.label];
    });

    var chart = new Chart(ctx, {
        // The type of chart we want to create
        type: 'line',

        // The data for our dataset
        data: {
            labels: labels,
            datasets: datasets
        },

        // Configuration options go here
        options: {
            elements: {
                line: {
                    fill: false,
                },
            },
        },
    });
}
