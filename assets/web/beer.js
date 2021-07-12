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

    var newLabels = [];
    var reg = /([0-9][0-9][0-9][0-9])([0-9][0-9])([0-9][0-9]) ([0-9]+)h([0-9]+)/;
    for (var l in labels) {
        var m = labels[l].match(reg)
        var d = new Date(parseInt(m[1]),
                         parseInt(m[2]),
                         parseInt(m[3]));
        d.setHours(parseInt(m[4]));
        d.setMinutes(parseInt(m[5]));
        newLabels.push(d.toISOString());
    }
    labels = newLabels;

    document.getElementById('total').innerHTML = 'Total drunk: ' + le_data['total'] + 'L'

    // Assign a color for each name.
    var nameToColor = {};
    for (var idx in drinkers) {
      nameToColor[drinkers[idx]] = "hsl(" + (360.0 * idx / drinkers.length).toFixed() + ", 50%, 50%)";
    }

    var ctx = document.getElementById('myChart').getContext('2d');

    datasets.forEach(function (item) {
        item.backgroundColor = nameToColor[item.label];
        item.borderColor = nameToColor[item.label];
        item.hoverBackgroundColor = nameToColor[item.label];
        item.hoverBorderColor = nameToColor[item.label];
    });

    var chart = new Chart(ctx, {
        // The type of chart we want to create
        type: 'line',

        // The data for our dataset
        data: {
            labels: labels,
            datasets: datasets,
        },

        // Configuration options go here
        options: {
            elements: {
                line: {
                    fill: false,
                    tension: 0,
                },
            },
            scales: {
                xAxes: [{
                    type: 'time',
                    time: {
                        tooltipFormat: 'ddd DD @ HH:mm',
                        unit: 'hour',
                        displayFormats: {
                            'hour': "ddd HH:MM"
                        },
                    }
                }],
            },
            monotone: 'monotone',
            tooltips: {
                callbacks: {
                    afterFooter: function(tooltip) {
                        // Datasets are sorted by amount. First index
                        // is the winner.
                        var prices = [
                            '\uD83E\uDD47', // gold
                            '\uD83E\uDD48', // silver
                            '\uD83E\uDD49', // bronze
                        ];
                        var text = '';
                        for (var i in tooltip) {
                            if (tooltip[i].datasetIndex < 3)
                                text += prices[tooltip[i].datasetIndex];
                        }
                        return text;
                    },
                },
                footerFontSize: 40,
            },
        },
    });
}
